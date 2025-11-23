from pydantic import BaseModel, EmailStr
from typing import List, Optional
from pydantic import BaseModel
from datetime import datetime
from typing import List, Optional, Dict, Any

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
    color: str
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




class CustomerOut(BaseModel):
    # The unique ID is the email/phone used for aggregation
    id: str 
    # Combined first name and last name, or fallback to email/phone
    name: str 
    email: Optional[str] = None
    phone: Optional[str] = None
    country: str
    city: str
    totalSpent: float
    lastOrder: datetime

    class Config:
        # Required for SQLAlchemy objects
        from_attributes = True

class CartItemIn(BaseModel):
    """Schema for a single line item (color/size combination) from the cart."""
    colorId: str
    size: str
    qty: int

class OrderDetailsIn(BaseModel):
    """The full order/invoice data from the cart page."""
    cartItems: List[CartItemIn]
    totalQuantity: int
    subtotal: float
    unitPrice: float
    colorNumberMap: Dict[str, int] # Not saved to DB, but useful for context
    productDetails: Dict[str, Any] # Product title, SKU, prices etc.

class CustomerInfoIn(BaseModel):
    """Schema for customer and shipping information from the checkout form."""
    emailOrPhone: str
    country: str
    firstName: str
    lastName: str
    address: str
    city: str
    postalCode: Optional[str] = None
    phone: Optional[str] = None
    saveInfo: Optional[bool] = False
    emailSubscription: Optional[bool] = False
    shippingMethod: str

class OrderSubmissionRequest(BaseModel):
    """The final request body combining order and customer data."""
    orderDetails: OrderDetailsIn
    customerInfo: CustomerInfoIn

# --- 2. Schemas for DB Models (Order Out) ---

class OrderItemOut(BaseModel):
    color_id: str
    color_name: str
    size: str
    quantity: int

    class Config:
        from_attributes = True

class OrderOut(BaseModel):
    id: int
    product_sku: str
    product_title: str
    total_quantity: int
    unit_price_tier: float
    grand_total: float
    
    email_or_phone: str
    first_name: str
    last_name: str
    address: str
    city: str
    country: str
    
    status: str
    created_at: datetime
    
    items: List[OrderItemOut] = []

    class Config:
        from_attributes = True