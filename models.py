# models.py
from sqlalchemy import Column, Integer, String, Float, ForeignKey
from sqlalchemy.orm import relationship
from database import Base


# Product model
class Product(Base):
    __tablename__ = "products"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, index=True)
    sku = Column(String, unique=True, index=True)
    gender = Column(String)
    category = Column(String)
    color = Column(String)
    description = Column(String)

    # Relationship to pricing tiers
    pricing_tiers = relationship("PricingTier", back_populates="product", cascade="all, delete-orphan")
    images = relationship("ProductImage", back_populates="product", cascade="all, delete-orphan")

class PricingTier(Base):
    __tablename__ = "pricing_tiers"

    id = Column(Integer, primary_key=True, index=True)
    product_id = Column(Integer, ForeignKey("products.id"))
    min_quantity = Column(Integer)
    price = Column(Float)

    product = relationship("Product", back_populates="pricing_tiers")

class ProductImage(Base):
    __tablename__ = "product_images"

    id = Column(Integer, primary_key=True, index=True)
    product_id = Column(Integer, ForeignKey("products.id"))
    image_url = Column(String) # You'll store paths or URLs to your images here

    product = relationship("Product", back_populates="images")