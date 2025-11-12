from fastapi import FastAPI, HTTPException
from schemas import EmailRequest
from email_utils import send_email
import os
import shutil
import uuid
from fastapi import FastAPI, Depends, HTTPException, UploadFile, File, Form
from fastapi.staticfiles import StaticFiles  # <-- Import this
from sqlalchemy.orm import Session
from typing import List, Optional
from fastapi.middleware.cors import CORSMiddleware
import models, schemas
from database import SessionLocal, engine, get_db
from sqlalchemy.orm import joinedload

models.Base.metadata.create_all(bind=engine)

app = FastAPI()


origins = [
    "http://localhost:5173", # Add your React app's URL here
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"], # Allows all methods (GET, POST, etc.)
    allow_headers=["*"], # Allows all headers
)
app.mount("/static", StaticFiles(directory="static"), name="static")
UPLOAD_DIRECTORY = "static/images"



@app.post("/send-email/")
async def send_email_endpoint(email: EmailRequest):
    """API endpoint to send an email"""
    result = send_email(email.to, email.subject, email.body)
    
    if result["status"] == "error":
        raise HTTPException(status_code=500, detail=result["message"])
    return result




# Create the database tables

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
    images: List[UploadFile] = File([]),
    db: Session = Depends(get_db)
):
    
    # --- Manually parse the strings into lists ---
    try:
        min_quantities = [int(q.strip()) for q in min_quantities_str.split(',') if q.strip()]
        prices = [float(p.strip()) for p in prices_str.split(',') if p.strip()]
    except ValueError:
        raise HTTPException(
            status_code=422, 
            detail="Invalid number format in min_quantities or prices. Ensure they are comma-separated numbers."
        )

    # --- Basic validation for pricing tiers ---
    if len(min_quantities) != len(prices):
        raise HTTPException(status_code=400, detail="Mismatch between min_quantities and prices for pricing tiers.")

    # --- Check for existing SKU ---
    db_product = db.query(models.Product).filter(models.Product.sku == sku).first()
    if db_product:
        raise HTTPException(status_code=400, detail="SKU already registered")

    # --- Create the product ---
    db_product = models.Product(
        title=title,
        sku=sku,
        gender=gender,
        category=category,
        color=color,
        description=description
    )
    db.add(db_product)
    db.commit()
    db.refresh(db_product)

    # --- Add pricing tiers ---
    for i in range(len(min_quantities)):
        db_pricing_tier = models.PricingTier(
            product_id=db_product.id,
            min_quantity=min_quantities[i],
            price=prices[i]
        )
        db.add(db_pricing_tier)

    # --- [START] MODIFIED IMAGE HANDLING ---
    
    # Ensure the upload directory exists
    os.makedirs(UPLOAD_DIRECTORY, exist_ok=True)

    for image_file in images:
        # Get the file extension (e.g., .png, .jpg)
        file_extension = os.path.splitext(image_file.filename)[1]
        
        # Create a unique filename using the SKU and a UUID
        unique_filename = f"{sku}_{uuid.uuid4()}{file_extension}"
        
        # Create the full file path (e.g., static/images/na-12_... .png)
        file_path = os.path.join(UPLOAD_DIRECTORY, unique_filename)
        
        # Save the file to the disk
        try:
            with open(file_path, "wb") as buffer:
                shutil.copyfileobj(image_file.file, buffer)
        finally:
            image_file.file.close() # Always close the uploaded file

        # This is the URL that will be stored in the DB and sent to the frontend
        # It matches the 'app.mount' path
        image_url = f"/static/images/{unique_filename}" 

        # Create the database record for the image
        db_product_image = models.ProductImage(
            product_id=db_product.id,
            image_url=image_url
        )
        db.add(db_product_image)
        
    # --- [END] MODIFIED IMAGE HANDLING ---

    db.commit()
    db.refresh(db_product)

    return db_product


#show all products
@app.get("/products/", response_model=List[schemas.ProductOut])
async def read_products(db: Session = Depends(get_db)):
    """
    Retrieve all products with their images and pricing tiers.
    """
    products = db.query(models.Product).options(
        joinedload(models.Product.images),
        joinedload(models.Product.pricing_tiers)
    ).all()
    return products



# --- 🗑️ ADD THIS ENDPOINT TO DELETE A PRODUCT ---
@app.delete("/products/{product_id}", status_code=204)
async def delete_product(product_id: int, db: Session = Depends(get_db)):
    """
    Delete a product by its ID.
    """
    db_product = db.query(models.Product).filter(models.Product.id == product_id).first()
    
    if db_product is None:
        raise HTTPException(status_code=404, detail="Product not found")

        
    db.delete(db_product)
    db.commit()
    return



#fetching products
@app.get("/specific/products/", response_model=List[schemas.ProductOut])
async def read_specific_products(
    gender: Optional[str] = None, 
    category: Optional[str] = None, 
    db: Session = Depends(get_db)
):
    """
    Retrieve products, optionally filtered by gender and category.
    Case-insensitive filtering is applied.
    """
    print(f"Gender : {gender}" )
    print(f"Category : {category}" )

    query = db.query(models.Product).options(
        joinedload(models.Product.images),
        joinedload(models.Product.pricing_tiers)
    )
    
    if gender:
        # ilike makes it case-insensitive (Mens matches mens)
        query = query.filter(models.Product.gender == gender)
    
    if category:
        # Handles cases like 'pants' vs 'pant' if you use simple contains
        # Or strictly match: query.filter(models.Product.category.ilike(category))
        query = query.filter(models.Product.category == category)

    products = query.all()
    return products