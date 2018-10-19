#!/usr/bin/env python
# All modules needed for this app
import random
import string
import httplib2
import json
import requests
from sqlalchemy import create_engine, asc
from sqlalchemy.orm import sessionmaker
from database_setup import Base, Category, Item, User
# add additional imports to support session tokens, the anti-forgery key
from flask import session as login_session
# Imports for GConnect.
from oauth2client.client import flow_from_clientsecrets
from oauth2client.client import FlowExchangeError
from flask import make_response
from flask import (Flask, render_template,
                   request, redirect, jsonify, url_for, flash)

app = Flask(__name__)

# Google Sign-in Client ID
CLIENT_ID = json.loads(open('client_secrets.json', 'r').read())[
                            'web']['client_id']


# Connect to Database and create database session
engine = create_engine('sqlite:///gearrental.db?check_same_thread=False')
Base.metadata.bind = engine

DBSession = sessionmaker(bind=engine)
session = DBSession()


# Create anti-forgery state token and login
@app.route('/login')
def showLogin():
    """Create anti-forgery state token and login"""
    state = ''.join(random.choice(string.ascii_uppercase + string.digits)
                    for x in xrange(32))
    login_session['state'] = state
    # return "The current session state is %s" % login_session['state']
    return render_template('login.html', STATE=state)


# Method to connect to third party Google Sign in
@app.route('/gconnect', methods=['POST'])
def gconnect():
    """Method to connect to third party Google Sign in"""
    # Validate state token
    if request.args.get('state') != login_session['state']:
        response = make_response(json.dumps('Invalid state parameter.'), 401)
        response.headers['Content-Type'] = 'application/json'
        return response

    # Obtain authorization code
    code = request.data

    try:
        # Upgrade the authorization code into a credentials object
        oauth_flow = flow_from_clientsecrets('client_secrets.json', scope='')
        oauth_flow.redirect_uri = 'postmessage'
        credentials = oauth_flow.step2_exchange(code)
    except FlowExchangeError:
        response = make_response(
            json.dumps('Failed to upgrade the authorization code.'), 401)
        response.headers['Content-Type'] = 'application/json'
        return response

    # Check that the access token is valid.
    access_token = credentials.access_token
    url = ('https://www.googleapis.com/oauth2/v1/tokeninfo?access_token=%s'
           % access_token)
    h = httplib2.Http()
    result = json.loads(h.request(url, 'GET')[1])

    # If there was an error in the access token info, abort.
    if result.get('error') is not None:
        response = make_response(json.dumps(result.get('error')), 500)
        response.headers['Content-Type'] = 'application/json'
        return response

    # Verify that the access token is used for the intended user.
    gplus_id = credentials.id_token['sub']
    if result['user_id'] != gplus_id:
        response = make_response(
            json.dumps("Token's user ID doesn't match given user ID."), 401)
        response.headers['Content-Type'] = 'application/json'
        return response

    # Verify that the access token is valid for this app.
    if result['issued_to'] != CLIENT_ID:
        response = make_response(
            json.dumps("Token's client ID does not match app's."), 401)
        print "Token's client ID does not match app's."
        response.headers['Content-Type'] = 'application/json'
        return response

    stored_access_token = login_session.get('access_token')
    stored_gplus_id = login_session.get('gplus_id')
    if stored_access_token is not None and gplus_id == stored_gplus_id:
        response = make_response(json.dumps(
            'Current user is already connected.'), 200)
        response.headers['Content-Type'] = 'application/json'
        return response

    # Store the access token in the session for later use.
    login_session['access_token'] = credentials.access_token
    login_session['gplus_id'] = gplus_id

    # Get user info
    userinfo_url = "https://www.googleapis.com/oauth2/v1/userinfo"
    params = {'access_token': credentials.access_token, 'alt': 'json'}
    answer = requests.get(userinfo_url, params=params)

    data = answer.json()

    login_session['username'] = data['name']
    login_session['picture'] = data['picture']
    login_session['email'] = data['email']

    user_id = getUserID(data['email'])
    if not user_id:
        user_id = createUser(login_session)
    login_session['user_id'] = user_id

    output = ''
    output += '<h1>Welcome, '
    output += login_session['username']
    output += '!</h1>'
    output += '<img src="'
    output += login_session['picture']
    output += ' " style = "width: 300px; height: 300px;border-radius: 150px;" \
        "-webkit-border-radius: 150px;-moz-border-radius: 150px;"> '
    flash("You are now logged in as %s" % login_session['username'])
    print "done!"
    return output


# Log out for Google Sign In
@app.route('/gdisconnect')
def gdisconnect():
    """Log out for Google Sign In"""
    access_token = login_session.get('access_token')
    if access_token is None:
        print 'Access Token is None'
        flash('Current user not connected.')
        return redirect(url_for('allCategories'))
    url = 'https://accounts.google.com/o/oauth2/revoke?token=%s' \
        % login_session['access_token']
    h = httplib2.Http()
    result = h.request(url, 'GET')[0]
    # Delete all login session stored variables
    if result['status'] == '200':
        del login_session['access_token']
        del login_session['gplus_id']
        del login_session['username']
        del login_session['email']
        del login_session['picture']
        del login_session['user_id']
        flash("You have successfully been logged out.")
        return redirect(url_for('allCategories'))
    else:
        response = make_response(
            json.dumps('Failed to revoke token for given user.', 400))
        response.headers['Content-Type'] = 'application/json'
        return response


# JSON Endpoint
# JSON of all categories and all items in the database
@app.route('/catalog.json/')
def allCatalogJSON():
    """JSON of all categories and all items in the database"""
    categories = session.query(Category).all()
    items = session.query(Item).order_by(Item.category_id).all()
    # joinquery= session.query(Category.id, Category.name,
    # Item.category_id, Item.title, Item.description,
    # Item.id).order_by(Category.id).all()
    return jsonify(Category=[i.serialize for i in categories], Item=[
        i.serialize for i in items])


# Return JSON of a specific item
@app.route('/catalog/item/<int:item_id>/JSON')
def oneItemJSON(item_id):
    """Return JSON of a specific item"""
    itemJSON = session.query(Item).filter_by(id=item_id).one()
    return jsonify(itemJSON=itemJSON.serialize)


# HTML Template Main Methods
# Display all categories
@app.route('/')
@app.route('/catalog')
def allCategories():
    """Display all categories"""
    categories = session.query(Category).all()
    if 'username' not in login_session:
        return render_template(
            'publicAllCategories.html', categories=categories)
    else:
        return render_template('allCategories.html', categories=categories)


# Display all items in one category
@app.route('/catalog/<int:category_id>/items/')
def categoryItems(category_id):
    """Display all items in one category"""
    categories = session.query(Category).all()
    itemCategory = session.query(Category).filter_by(id=category_id).one()
    items = session.query(Item).filter_by(category_id=itemCategory.id)
    if 'username' not in login_session:
        return render_template(
            'publicCategoryItems.html',
            categories=categories, itemCategory=itemCategory, items=items)
    else:
        return render_template(
            'categoryItems.html',
            categories=categories, itemCategory=itemCategory, items=items)


# Show a specific item in a category.
# Only display edit and delete to the user who created the item
@app.route('/catalog/<int:category_id>/<int:item_id>/')
def showItem(category_id, item_id):
    """Show a specific item in a category.
    Only display edit and delete to the user who created the item"""
    showItem = session.query(Item).filter_by(id=item_id).one()
    creator = getUserInfo(showItem.user_id)
    if 'username' not in login_session or \
            creator.id != login_session['user_id']:
        return render_template(
            'publicShowItem.html', showItem=showItem, category_id=category_id)
    else:
        return render_template(
            'showItem.html', showItem=showItem, category_id=category_id)


# Create a new item
@app.route('/catalog/new/', methods=['GET', 'POST'])
def newItem():
    """Create a new item"""
    categories = session.query(Category).all()
    if 'username' not in login_session:
        return redirect('/login')
    if request.method == 'POST':
        newItem = Item(title=request.form['title'], description=request.form[
            'description'], category_id=categoryID(
                request.form["category"]), user_id=login_session['user_id'])
        session.add(newItem)
        session.commit()
        flash("The new item %s was created" % newItem.title)
        return redirect(url_for('allCategories'))
    else:
        return render_template('newItem.html', categories=categories)


# Edit the selected item if the user is
# the the creator of the item, if not redirect to login page
@app.route('/catalog/<int:item_id>/edit/', methods=['GET', 'POST'])
def editItem(item_id):
    """Edit the selected item if the user is
    the the creator of the item, if not redirect to login page"""
    categories = session.query(Category).all()
    if 'username' not in login_session:
        return redirect('/login')
    editedItem = session.query(Item).filter_by(id=item_id).one()
    if login_session['user_id'] != editedItem.user_id:
        return "<script>function myFunction(){alert('You are not " \
            "authorized to edit this item. Please create your own item " \
            "to be able to edit them.');}</script><body onload='myFunction()'>"
    if request.method == 'POST':
        if request.form['title']:
            editedItem.title = request.form['title']
        if request.form['description']:
            editedItem.description = request.form['description']
        if request.form['category']:
            editedItem.category_id = categoryID(request.form['category'])
        session.add(editedItem)
        session.commit()
        flash("The item %s was edited" % editedItem.title)
        return redirect(url_for('allCategories'))
    else:
        return render_template(
            'editItem.html', editedItem=editedItem, categories=categories)


# Delete the selected item if the user
# is the the creator of the item, if not redirect to login page
@app.route('/catalog/<int:item_id>/delete/', methods=['GET', 'POST'])
def deleteItem(item_id):
    """Delete the selected item if the user
    is the the creator of the item, if not redirect to login page"""
    deletedItem = session.query(Item).filter_by(id=item_id).one()
    if 'username' not in login_session:
        return redirect('/login')
    if deletedItem.user_id != login_session['user_id']:
        return "<script>function myFunction(){alert('You are not " \
            "authorized to delete this item. Please create your own item " \
            "in order to be able to delete it.')" \
            ";}</script><body onload='myFunction()'>"
    if request.method == 'POST':
        session.delete(deletedItem)
        session.commit()
        flash("The item  %s was succesfully deleted" % deletedItem.title)
        return redirect(url_for('allCategories'))
    else:
        return render_template('deleteItem.html', deletedItem=deletedItem)


# If a user ID is passed into this method,
# it returns the user object associated with the ID
def getUserInfo(user_id):
    """If a user ID is passed into this method,
    it returns the user object associated with the ID"""
    user = session.query(User).filter_by(id=user_id).one()
    return user


# Takes an email address and return a user id if
# this email address belongs to a user stored in the DB
def getUserID(email):
    """Takes an email address and return a user id if
    this email address belongs to a user stored in the DB"""
    user = session.query(User).filter_by(email=email).one_or_none()
    if user != None:
        return user.id
    else:
        return None


# creates a new user in the table user and
# extracts all the field to populate the table
def createUser(login_session):
    """creates a new user in the table user and
    extracts all the field to populate the table"""
    newUser = User(name=login_session['username'], email=login_session[
                   'email'], picture=login_session['picture'])
    session.add(newUser)
    session.commit()
    # pull the info from the newly create user item in the table user
    user = session.query(User).filter_by(
        email=login_session['email']).one()
    return user.id


# Helper function for newItem and editItem.
# Input the category name, output the category id
def categoryID(category):
    """Helper function for newItem and editItem.
    Input the category name, output the category id"""
    whichCategory = session.query(Category).filter_by(name=category).one()
    category_id = whichCategory.id
    return category_id


if __name__ == '__main__':
    app.secret_key = 'super_secret_key'
    app.debug = True
    app.run(host='0.0.0.0', port=8000)
