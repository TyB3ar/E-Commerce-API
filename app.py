from flask import Flask, jsonify, request
from flask_sqlalchemy import SQLAlchemy
from flask_marshmallow import Marshmallow
from marshmallow import fields, ValidationError, validate
import mysql.connector
from mysql.connector import Error
from Password import Password
from datetime import datetime, timedelta
from order_shipment import calculate_delivery_date, calculate_ship_date

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = f'mysql+mysqlconnector://root:{Password}@localhost/e_commerce_db'
db = SQLAlchemy(app)
ma = Marshmallow(app)

class CustomerSchema(ma.Schema):   # Schema for 'customers'
    name = fields.String(required=True) 
    email = fields.String(required=True)
    phone = fields.String(required=True)
    
    class Meta:
        fields = ("name", "email", "phone", "id") 
        

customer_schema = CustomerSchema()
customers_schema = CustomerSchema(many=True) 

class Customer(db.Model):   # table for 'customers' 
    __tablename__ = 'Customers'
    id = db.Column(db.Integer, primary_key=True) 
    name = db.Column(db.String(255), nullable=False)
    email = db.Column(db.String(320)) 
    phone = db.Column(db.String(15)) 
    orders = db.relationship('Order', backref='customer') # one-to-many relationship between customers and orders
    
    
# Relationship between orders and products: 
order_products = db.Table('order_products', 
        db.Column('order_id', db.Integer, db.ForeignKey('Orders.id'), primary_key=True),
        db.Column('product_id', db.Integer, db.ForeignKey('Products.id'), primary_key=True),
)        


class ProductSchema(ma.Schema):   # Schema for 'products' 
    name = fields.String(required=True, validate=validate.Length(min=1))
    price = fields.Float(required=True, validate=validate.Range(min=0))

product_schema = ProductSchema()
products_schema = ProductSchema(many=True)

class Product(db.Model):   # table for 'products' 
    __tablename__ = 'Products'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(255), nullable=False)
    price = db.Column(db.Float, nullable=False)
    orders = db.relationship('Order', secondary='order_products', backref=db.backref('products'))


class OrderSchema(ma.Schema):   # Schema for 'orders' 
    order_date = fields.String(required=True)
    customer_id = fields.String(required=True)
    products = fields.Nested(ProductSchema, many=True)
    
    class Meta:
        fields = ('id' , 'order_date', 'customer_id', 'ship_date', 'delivery_date', 'products')   
        
order_schema = OrderSchema()
orders_schema = OrderSchema(many=True) 

class Order(db.Model):   # table for 'orders'
    __tablename__ = 'Orders'
    id = db.Column(db.Integer, primary_key=True)
    order_date = db.Column(db.Date, nullable=False) 
    ship_date = db.Column(db.Date)
    delivery_date = db.Column(db.Date) 
    customer_id = db.Column(db.Integer, db.ForeignKey('Customers.id'))
    product_id = db.Column(db.Integer, db.ForeignKey('Products.id'))


class CustomerAccountSchema(ma.Schema):   # Schema for 'customer_accounts' 
    username = fields.String(required=True)
    password = fields.String(required=True)
    customer_id = fields.String(required=True)
    
    class Meta:
        fields = ("id", "username", "password", "customer_id") 
        
customer_account_schema = CustomerAccountSchema()
customer_accounts_schema = CustomerAccountSchema(many=True) 

class CustomerAccount(db.Model):   # table for 'customer_accounts' 
    __tablename__ = 'Customer_Accounts'
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(255), unique=True, nullable=False)
    password = db.Column(db.String(255), nullable=False)
    customer_id = db.Column(db.Integer, db.ForeignKey('Customers.id'))
    customer = db.relationship('Customer', backref='customer_account', uselist=False) # establishes relationship, one-to-one
    
  
# Customer Management: DONE 
@app.route('/customers', methods=["GET"])   # GET method to retrieve all customer info
def get_customers():
    customers = Customer.query.all()
    return customers_schema.jsonify(customers) 

@app.route('/customers/<int:id>', methods=["GET"])   # GET method to retrieve specific customer info 
def get_customer(id):
    customer = Customer.query.get_or_404(id) 
    return customer_schema.jsonify(customer)     

@app.route('/customers', methods=["POST"])   # POST method to add new customer
def add_customer():
    try:
        customer_data = customer_schema.load(request.json)     
    except ValidationError as err:
        return jsonify(err.messages), 400 
    
    new_customer = Customer(name=customer_data['name'], email=customer_data['email'], phone=customer_data['phone'])
    db.session.add(new_customer) 
    db.session.commit()
    return jsonify({"message" : "New customer added successfully"}), 201 

@app.route('/customers/<int:id>', methods=["PUT"])   # PUT method to update customer info
def update_customer(id):
    customer = Customer.query.get_or_404(id) 
    try:
        customer_data = customer_schema.load(request.json)        
    except ValidationError as err:
        return jsonify(err.messages), 400
    
    customer.name = customer_data['name']
    customer.email = customer_data['email']
    customer.phone = customer_data['phone'] 
    db.session.commit()
    return jsonify({"message": "Customer details updated successfully"}), 200

@app.route('/customers/<int:id>', methods=["DELETE"])   # DELETE method to remove customer
def delete_customer(id):
    customer = Customer.query.get_or_404(id) 
    db.session.delete(customer)  
    db.session.commit()
    return jsonify({"message" : "Customer removed successfully"}), 200 


# Customer Account Management: DONE
@app.route('/customers/<int:customer_id>/customeraccount', methods=["GET"])   # GET method to retrieve specific customer account (include customer info)
def get_customer_accounts(customer_id):
    customer_account = CustomerAccount.query.filter_by(customer_id=customer_id).first_or_404()  # retireve customer account linked to customer id 
    customer = Customer.query.get_or_404(customer_id)  # retrieve customer by customer id
    # set result to dictionary to return info as for json 
    result = {
        'account_id' : customer_account.id, 
        'username' : customer_account.username,
        'customer_id' : customer_account.customer_id,
        'customer_name' : customer.name,
        'customer_email' : customer.email,
        'customer_phone' : customer.phone
    }
    return jsonify(result), 200 

@app.route('/customeraccount', methods=["POST"])   # POST method to add new customer account
def add_customer_account():
    try:
        customer_account_data = customer_account_schema.load(request.json)
    except ValidationError as err:
        return jsonify(err.messages), 400 
    
    new_customer_account = CustomerAccount(username=customer_account_data['username'], password=customer_account_data['password'], customer_id=customer_account_data['customer_id']) 
    db.session.add(new_customer_account) 
    db.session.commit()
    return jsonify({"message" : "New customer account added successfully"}), 201  

@app.route('/customeraccount/<int:id>', methods=["PUT"])   # PUT method to update customer account
def update_customer_account(id):
    customer_account = CustomerAccount.query.get_or_404(id) 
    try:
        customer_account_data = customer_account_schema.load(request.json)
    except ValidationError as err:
        return jsonify(err.messages), 400 
    
    customer_account.username = customer_account_data['username']
    customer_account.password = customer_account_data['password'] 
    
    db.session.commit()
    return jsonify({"message" : "Customer account updated successfully"}), 201

@app.route('/customeraccount/<int:id>', methods=["DELETE"])   # DELETE method to remove customer account
def remove_customer_account(id):
    customer_account = CustomerAccount.query.get_or_404(id)
    db.session.delete(customer_account)
    db.session.commit()
    return jsonify({"message" : "Customer account removed successfully"}), 200 


# Product Management: DONE
@app.route('/products/<int:id>', methods=["GET"])   # GET method for product information by id
def get_product(id):   
    product = Product.query.get_or_404(id)
    return product_schema.jsonify(product) 

@app.route('/products', methods=["POST"])   # POST method to add new product
def add_product():
    try:
        product_data = product_schema.load(request.json)
    except ValidationError as err:
        return jsonify(err.messages), 400
    
    new_product = Product(name=product_data['name'], price=product_data['price'])
    db.session.add(new_product)
    db.session.commit()
    return jsonify({"message" : "Product added successfully"}), 201

@app.route('/products/<int:id>', methods=["PUT"])   # PUT method to update product information
def update_product(id):
    product = Product.query.get_or_404(id)
    try:
        product_data = product_schema.load(request.json)
    except ValidationError as err:
        return jsonify(err.messages), 400
    
    product.name = product_data['name']
    product.price = product_data['price']
    db.session.commit()
    return jsonify({"message" : "Product updated successfully"}), 201

@app.route('/products/<int:id>', methods=["DELETE"])   # DELETE method to remove product from catalog
def remove_product(id):
    product = Product.query.get_or_404(id)
    db.session.delete(product)
    db.session.commit()
    return jsonify({"message" : "Product removed successfully"}), 201    

@app.route('/products', methods=["GET"])   # GET method to list all products in catalog
def list_products():
    products = Product.query.all()
    return products_schema.jsonify(products) 


# Order Processing:
@app.route('/orders', methods=["POST"])   # POST method to process new orders, need order date/customer id/ product name. Include functions to add ship and delivery dates 
def process_order():
    try:
        order_data = request.json
        order_date_str = order_data['order_date'] 
        order_date = datetime.strptime(order_date_str, '%Y-%m-%d')
        customer_id = order_data['customer_id'] 
        product_id = order_data['product_id']
        
        shipment_days = order_data.get('shipment_days', 2)
        delivery_days = order_data.get('delivery_days', 5)
        ship_date = calculate_ship_date(order_date, shipment_days)
        delivery_date = calculate_delivery_date(order_date, delivery_days)
        
        new_order = Order(
            order_date=order_date,
            ship_date=ship_date,
            delivery_date=delivery_date,
            customer_id=customer_id,
            product_id=product_id
        )    
        
        db.session.add(new_order) # add and commit new order
        db.session.commit()
         
        for p_id in product_id:    # manually enter in order_id and product_id from new_order
            product = Product.query.get(product_id)
            if product:
                insert_ids = order_products.insert().values(order_id=new_order.id, product_id=product.id)
                db.session.execute(insert_ids) 
        
        db.session.commit()   # commits adding order_id and product_id to order_products table 
        
        return jsonify({"message" : "Order processed successfully"}), 201
    
    except ValidationError as err:
        return jsonify(err.messages), 400
    except Exception as e:
        return jsonify({"Error" : str(e)}), 500 
            
@app.route('/orders/<int:id>', methods=["GET"])   # GET method to track order date and delivery date 
def track_order(id):
    order = Order.query.get_or_404(id)  # Serialize/deserialize data from Order table
    return jsonify({        # return json of organized data from the table, mainly order date, ship date, and delivery date
        'order_date' : order.order_date.strftime('%Y-%m-%d'), 
        'ship_date' : order.ship_date.strftime('%Y-%m-%d'),
        'delivery_date' : order.delivery_date.strftime('%Y-%m-%d') 
    }), 200

@app.route('/orders/<int:id>/products', methods=["GET"])   # GET method to retrieve specific details of order, include order date/ship date/delivery date/products/customer id 
def detail_order(id):
    try:
        order = Order.query.get_or_404(id)
        
        result = {
            'order_id' : order.id,
            'order_date' : order.order_date.strftime('%Y-%m-%d'),
            'ship_date' : order.ship_date.strftime('%Y-%m-%d'),
            'delivery_date' : order.delivery_date.strftime('%Y-%m-%d'),
            'customer_id' : order.customer_id,
            'products' : [{'product_id' : p.id, 'product_name' : p.name, 'price' : p.price} for p in order.products]
        }
        
        return jsonify(result) 
        
    except ValidationError as err:
        return jsonify(err.messages), 400   

@app.route('/customers/<int:customer_id>/orders', methods=["GET"])   # GET method to view customer order history
def order_history(customer_id):
    try: 
        orders = Order.query.filter_by(customer_id=customer_id).all() 
        if not orders:
            return jsonify({"message" : "No orders found for that customer"})
        
        result = orders_schema.dump(orders)
        
        return jsonify(result), 200   
    
    except ValidationError as err:
        return jsonify(err.messages), 400
    except Error as e:
        return jsonify({"Error" : str(e)}), 500
    
 
if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True) 
    