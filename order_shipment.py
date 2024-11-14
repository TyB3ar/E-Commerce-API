# Module for calculating order shipment and delivery dates 

from datetime import datetime, timedelta

def calculate_ship_date(order_date, shipment_days): # add 'days_till_shipment' to order date for ship date
    return order_date + timedelta(days=shipment_days) 
    

def calculate_delivery_date(order_date, delivery_days): # add 'days_till_delivery' to order date for delivery date
    return order_date + timedelta(days=delivery_days) 


