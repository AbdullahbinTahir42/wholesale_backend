from pydantic import BaseModel, EmailStr
from typing import List, Optional
from pydantic import BaseModel

class EmailRequest(BaseModel):
    to: EmailStr
    subject: str
    body: str



# Product schemas

class PricingTierBase(BaseModel):
    min_quantity: int
    price: float

class PricingTierCreate(PricingTierBase):
    pass

class PricingTierOut(PricingTierBase):
    id: int
    product_id: int

    class Config:
        from_attributes = True

class ProductImageBase(BaseModel):
    image_url: str

class ProductImageCreate(ProductImageBase):
    pass

class ProductImageOut(ProductImageBase):
    id: int
    product_id: int

    class Config:
        from_attributes = True

class ProductBase(BaseModel):
    title: str
    sku: str
    gender: str
    category: str
    color: str
    description: Optional[str] = None

class ProductCreate(ProductBase):
    # For form data, we'll handle tiers and images separately
    pass

class ProductOut(ProductBase):
    id: int
    pricing_tiers: List[PricingTierOut] = []
    images: List[ProductImageOut] = []

    class Config:
        from_attributes = True