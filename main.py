from fastapi import FastAPI, HTTPException, Depends, UploadFile, File, Form
from fastapi.staticfiles import StaticFiles
from sqlalchemy.orm import Session, joinedload, aliased # 🎯 FIX: Explicitly importing aliased here
from sqlalchemy import func, cast, String, select
from typing import List, Optional, Dict, Any
from fastapi.middleware.cors import CORSMiddleware
import os
import shutil
import uuid
from datetime import datetime

# Assuming you have database, models, schemas, and email_utils defined
import models, schemas
from database import SessionLocal, engine, get_db
from email_utils import send_email # Assuming this utility exists
from schemas import OrderOut, OrderItemOut, OrderSubmissionRequest, EmailRequest # Ensuring user's explicit imports are covered

# Create the database tables
models.Base.metadata.create_all(bind=engine)

app = FastAPI()

origins = [
    "http://localhost:5173", # Add your React app's URL here
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.mount("/static", StaticFiles(directory="static"), name="static")
UPLOAD_DIRECTORY = "static/images"


# --- EXISTING ENDPOINTS ---

@app.post("/send-email/")
async def send_email_endpoint(email: EmailRequest):
    """API endpoint to send an email"""
    result = send_email(email.to, email.subject, email.body)
    
    if result["status"] == "error":
        raise HTTPException(status_code=500, detail=result["message"])
    return result

@app.post("/products/", response_model=schemas.ProductOut)
async def create_product(
    title: str = Form(...),
    sku: str = Form(...),
    gender: str = Form(...),
    category: str = Form(...),
    color: str = Form(...),
    description: Optional[str] = Form(None),
    min_quantities_str: str = Form(..., alias="min_quantities"),
    prices_str: str = Form(..., alias="prices"),
    image_colors_str: str = Form(..., alias="image_colors"), 
    images: List[UploadFile] = File([]),
    db: Session = Depends(get_db)
):
    try:
        min_quantities = [int(q.strip()) for q in min_quantities_str.split(',') if q.strip()]
        prices = [float(p.strip()) for p in prices_str.split(',') if p.strip()]
    except ValueError:
        raise HTTPException(status_code=422, detail="Invalid pricing format")

    image_colors = [c.strip() for c in image_colors_str.split(',') if c.strip()]

    if len(images) != len(image_colors):
        raise HTTPException(status_code=400, detail=f"You uploaded {len(images)} images but provided {len(image_colors)} color names. They must match.")

    db_product = db.query(models.Product).filter(models.Product.sku == sku).first()
    if db_product:
        raise HTTPException(status_code=400, detail="SKU already registered")

    db_product = models.Product(
        title=title, sku=sku, gender=gender, category=category, color=color, description=description
    )
    db.add(db_product)
    db.commit()
    db.refresh(db_product)

    for i in range(len(min_quantities)):
        db_pricing_tier = models.PricingTier(product_id=db_product.id, min_quantity=min_quantities[i], price=prices[i])
        db.add(db_pricing_tier)

    os.makedirs(UPLOAD_DIRECTORY, exist_ok=True)
    for image_file, color_name in zip(images, image_colors):
        file_extension = os.path.splitext(image_file.filename)[1]
        unique_filename = f"{sku}_{color_name}_{uuid.uuid4()}{file_extension}"
        file_path = os.path.join(UPLOAD_DIRECTORY, unique_filename)
        
        try:
            with open(file_path, "wb") as buffer:
                shutil.copyfileobj(image_file.file, buffer)
        finally:
            image_file.file.close()

        image_url = f"/static/images/{unique_filename}" 

        db_product_image = models.ProductImage(
            product_id=db_product.id,
            image_url=image_url,
            color=color_name
        )
        db.add(db_product_image)
        
    db.commit()
    db.refresh(db_product)
    return db_product

@app.get("/products/", response_model=List[schemas.ProductOut])
async def read_products(db: Session = Depends(get_db)):
    products = db.query(models.Product).options(
        joinedload(models.Product.images),
        joinedload(models.Product.pricing_tiers)
    ).all()
    return products

@app.delete("/products/{product_id}", status_code=204)
async def delete_product(product_id: int, db: Session = Depends(get_db)):
    db_product = db.query(models.Product).filter(models.Product.id == product_id).first()
    if db_product is None:
        raise HTTPException(status_code=404, detail="Product not found")
    db.delete(db_product)
    db.commit()
    return

@app.get("/specific/products/", response_model=List[schemas.ProductOut])
async def read_specific_products(
    gender: Optional[str] = None, 
    category: Optional[str] = None, 
    db: Session = Depends(get_db)
):
    query = db.query(models.Product).options(
        joinedload(models.Product.images),
        joinedload(models.Product.pricing_tiers)
    )
    if gender:
        query = query.filter(models.Product.gender == gender)
    if category:
        query = query.filter(models.Product.category == category)
    products = query.all()
    return products

@app.get("/products/{product_id}", response_model=schemas.ProductOut)
async def read_product(product_id: int, db: Session = Depends(get_db)):
    product = db.query(models.Product).options(
        joinedload(models.Product.images),
        joinedload(models.Product.pricing_tiers)
    ).filter(models.Product.id == product_id).first()
    if product is None:
        raise HTTPException(status_code=404, detail="Product not found")
    return product


# ----------------------------------------------------------------------
# 🛍️ NEW: ORDER SUBMISSION ENDPOINT 🛍️
# ----------------------------------------------------------------------

@app.post("/orders/submit/", response_model=schemas.OrderOut, status_code=201)
async def submit_order(
    request: schemas.OrderSubmissionRequest, 
    db: Session = Depends(get_db)
):
    # Extract data
    customer_info = request.customerInfo
    order_details = request.orderDetails
    
    # Map front-end color ID to real color name
    color_map = {c['id']: c['name'] for c in order_details.productDetails['colors']}
    
    # 1. Create the main Order entry
    db_order = models.Order(
        # General/Financial details
        product_sku=order_details.productDetails['sku'],
        product_title=order_details.productDetails['title'],
        total_quantity=order_details.totalQuantity,
        unit_price_tier=order_details.unitPrice,
        grand_total=order_details.subtotal,
        
        # Customer details
        email_or_phone=customer_info.emailOrPhone,
        first_name=customer_info.firstName,
        last_name=customer_info.lastName,
        address=customer_info.address,
        city=customer_info.city,
        country=customer_info.country,
        postal_code=customer_info.postalCode,
        phone=customer_info.phone,
        shipping_method=customer_info.shippingMethod,
        
        status="Confirmed"
    )
    
    db.add(db_order)
    db.commit()
    db.refresh(db_order)

    # 2. Create the OrderItem entries
    for item in order_details.cartItems:
        color_name = color_map.get(item.colorId, item.colorId) 
        
        db_item = models.OrderItem(
            order_id=db_order.id,
            color_id=item.colorId,
            color_name=color_name,
            size=item.size,
            quantity=item.qty
        )
        db.add(db_item)
        
    db.commit()
    db.refresh(db_order)

    return db_order


@app.get("/orders/", response_model=List[OrderOut])
async def read_orders(db: Session = Depends(get_db)):
    """
    Retrieve all orders with their associated line items (order_items)
    """
    orders = db.query(models.Order).options(
        joinedload(models.Order.items)
    ).order_by(models.Order.created_at.desc()).all()

    for order in orders:
        # We attach an invoice number for the frontend UI.
        order.invoice = f"INV-{order.id:06}"
    return orders


# ----------------------------------------------------------------------
# 📈 NEW: CUSTOMER AGGREGATION ENDPOINT 📈
# ----------------------------------------------------------------------

@app.get("/customers/", response_model=List[schemas.CustomerOut])
async def read_customers(db: Session = Depends(get_db)):
    """
    Retrieves and aggregates customer data from the Orders table.
    Groups orders by the unique customer ID (email_or_phone) 
    to calculate total spent and last order date.
    """
    
    # --- 1. Subquery: Aggregate metrics (Total Spent, Last Order Date, Latest Order ID) ---
    subquery = db.query(
        models.Order.email_or_phone.label('customer_id'),
        func.max(models.Order.id).label('latest_order_id'), 
        func.sum(models.Order.grand_total).label('totalSpent'),
        func.max(models.Order.created_at).label('lastOrder')
    ).group_by(models.Order.email_or_phone).subquery()
    
    # 🎯 FIX APPLIED: Use aliased() is correctly defined in the imports.
    orders_alias = aliased(models.Order)
    
    query = db.query(
        subquery.c.customer_id.label('id'),
        
        # Fetch the customer details associated with the latest order ID
        orders_alias.first_name,
        orders_alias.last_name,
        orders_alias.country,
        orders_alias.city,
        orders_alias.phone,
        
        # Aggregated fields
        subquery.c.totalSpent,
        subquery.c.lastOrder
        
    ).join(
        orders_alias, 
        orders_alias.id == subquery.c.latest_order_id
    ).order_by(subquery.c.lastOrder.desc())
    
    results = query.all()
    
    customers_data = []
    for row in results:
        is_email = "@" in row.id
        email = row.id if is_email else None
        phone = row.phone if row.phone else (row.id if not is_email else None)

        full_name = f"{row.first_name or ''} {row.last_name or ''}".strip()
        
        customers_data.append(schemas.CustomerOut(
            id=row.id,
            name=full_name or row.id,
            email=email,
            phone=phone,
            country=row.country,
            city=row.city,
            totalSpent=row.totalSpent,
            lastOrder=row.lastOrder
        ))
        
    return customers_data