from fastapi import FastAPI, APIRouter, HTTPException, Depends, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
import os
import logging
from pathlib import Path
from pydantic import BaseModel, Field
from typing import List, Optional
import uuid
from datetime import datetime, timedelta
import jwt
import bcrypt
from email_validator import validate_email, EmailNotValidError

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

# MongoDB connection
mongo_url = os.environ['MONGO_URL']
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ['DB_NAME']]

# JWT settings
JWT_SECRET = os.environ.get('JWT_SECRET', 'your-secret-key-here')
JWT_ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_HOURS = 24

# Create the main app without a prefix
app = FastAPI(title="Hair Ecommerce API")

# Create a router with the /api prefix
api_router = APIRouter(prefix="/api")

# Security
security = HTTPBearer()

# Models
class User(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    email: str
    first_name: str
    last_name: str
    password_hash: str
    created_at: datetime = Field(default_factory=datetime.utcnow)
    is_active: bool = True

class UserCreate(BaseModel):
    email: str
    first_name: str
    last_name: str
    password: str

class UserLogin(BaseModel):
    email: str
    password: str

class UserResponse(BaseModel):
    id: str
    email: str
    first_name: str
    last_name: str
    created_at: datetime
    is_active: bool

class Product(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str
    description: str
    price: float
    category: str  # extensions, wigs, bundles, closures, hair_care, accessories
    subcategory: Optional[str] = None
    images: List[str]
    attributes: dict = {}  # length, color, texture, etc.
    stock_quantity: int
    is_active: bool = True
    created_at: datetime = Field(default_factory=datetime.utcnow)

class ProductCreate(BaseModel):
    name: str
    description: str
    price: float
    category: str
    subcategory: Optional[str] = None
    images: List[str]
    attributes: dict = {}
    stock_quantity: int

class CartItem(BaseModel):
    product_id: str
    quantity: int
    price: float

class Cart(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    user_id: str
    items: List[CartItem] = []
    total_amount: float = 0.0
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

class Order(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    user_id: str
    items: List[CartItem]
    total_amount: float
    status: str = "pending"  # pending, processing, shipped, delivered, cancelled
    shipping_address: dict
    payment_method: str
    created_at: datetime = Field(default_factory=datetime.utcnow)

class OrderCreate(BaseModel):
    items: List[CartItem]
    shipping_address: dict
    payment_method: str

# Utility functions
def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

def verify_password(password: str, hashed: str) -> bool:
    return bcrypt.checkpw(password.encode('utf-8'), hashed.encode('utf-8'))

def create_access_token(data: dict):
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(hours=ACCESS_TOKEN_EXPIRE_HOURS)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, JWT_SECRET, algorithm=JWT_ALGORITHM)
    return encoded_jwt

async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    try:
        payload = jwt.decode(credentials.credentials, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        user_id: str = payload.get("sub")
        if user_id is None:
            raise HTTPException(status_code=401, detail="Invalid token")
    except jwt.PyJWTError:
        raise HTTPException(status_code=401, detail="Invalid token")
    
    user = await db.users.find_one({"id": user_id})
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")
    return User(**user)

# Auth routes
@api_router.post("/auth/register", response_model=UserResponse)
async def register(user_data: UserCreate):
    # Validate email
    try:
        validate_email(user_data.email)
    except EmailNotValidError:
        raise HTTPException(status_code=400, detail="Invalid email format")
    
    # Check if user exists
    existing_user = await db.users.find_one({"email": user_data.email})
    if existing_user:
        raise HTTPException(status_code=400, detail="Email already registered")
    
    # Create user
    user_dict = user_data.dict()
    user_dict['password_hash'] = hash_password(user_dict.pop('password'))
    user_obj = User(**user_dict)
    
    await db.users.insert_one(user_obj.dict())
    return UserResponse(**user_obj.dict())

@api_router.post("/auth/login")
async def login(user_data: UserLogin):
    user = await db.users.find_one({"email": user_data.email})
    if not user or not verify_password(user_data.password, user['password_hash']):
        raise HTTPException(status_code=401, detail="Invalid email or password")
    
    access_token = create_access_token(data={"sub": user['id']})
    return {"access_token": access_token, "token_type": "bearer", "user": UserResponse(**user)}

@api_router.get("/auth/me", response_model=UserResponse)
async def get_current_user_info(current_user: User = Depends(get_current_user)):
    return UserResponse(**current_user.dict())

# Product routes
@api_router.get("/products", response_model=List[Product])
async def get_products(category: Optional[str] = None, limit: int = 50):
    query = {"is_active": True}
    if category:
        query["category"] = category
    
    products = await db.products.find(query).limit(limit).to_list(limit)
    return [Product(**product) for product in products]

@api_router.get("/products/{product_id}", response_model=Product)
async def get_product(product_id: str):
    product = await db.products.find_one({"id": product_id, "is_active": True})
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    return Product(**product)

@api_router.post("/products", response_model=Product)
async def create_product(product_data: ProductCreate):
    product_obj = Product(**product_data.dict())
    await db.products.insert_one(product_obj.dict())
    return product_obj

# Cart routes
@api_router.get("/cart", response_model=Cart)
async def get_cart(current_user: User = Depends(get_current_user)):
    cart = await db.carts.find_one({"user_id": current_user.id})
    if not cart:
        # Create empty cart
        cart_obj = Cart(user_id=current_user.id)
        await db.carts.insert_one(cart_obj.dict())
        return cart_obj
    return Cart(**cart)

@api_router.post("/cart/add")
async def add_to_cart(product_id: str, quantity: int = 1, current_user: User = Depends(get_current_user)):
    # Get product
    product = await db.products.find_one({"id": product_id, "is_active": True})
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    
    # Get or create cart
    cart = await db.carts.find_one({"user_id": current_user.id})
    if not cart:
        cart_obj = Cart(user_id=current_user.id)
        cart = cart_obj.dict()
        await db.carts.insert_one(cart)
    
    # Check if item already in cart
    cart_items = cart.get('items', [])
    existing_item = None
    for item in cart_items:
        if item['product_id'] == product_id:
            existing_item = item
            break
    
    if existing_item:
        existing_item['quantity'] += quantity
    else:
        cart_items.append({
            "product_id": product_id,
            "quantity": quantity,
            "price": product['price']
        })
    
    # Calculate total
    total = sum(item['quantity'] * item['price'] for item in cart_items)
    
    await db.carts.update_one(
        {"user_id": current_user.id},
        {"$set": {"items": cart_items, "total_amount": total, "updated_at": datetime.utcnow()}}
    )
    
    return {"message": "Item added to cart", "total_items": len(cart_items)}

@api_router.delete("/cart/remove/{product_id}")
async def remove_from_cart(product_id: str, current_user: User = Depends(get_current_user)):
    cart = await db.carts.find_one({"user_id": current_user.id})
    if not cart:
        raise HTTPException(status_code=404, detail="Cart not found")
    
    cart_items = [item for item in cart.get('items', []) if item['product_id'] != product_id]
    total = sum(item['quantity'] * item['price'] for item in cart_items)
    
    await db.carts.update_one(
        {"user_id": current_user.id},
        {"$set": {"items": cart_items, "total_amount": total, "updated_at": datetime.utcnow()}}
    )
    
    return {"message": "Item removed from cart"}

# Order routes
@api_router.post("/orders", response_model=Order)
async def create_order(order_data: OrderCreate, current_user: User = Depends(get_current_user)):
    total_amount = sum(item.quantity * item.price for item in order_data.items)
    
    order_dict = order_data.dict()
    order_dict['user_id'] = current_user.id
    order_dict['total_amount'] = total_amount
    order_obj = Order(**order_dict)
    
    await db.orders.insert_one(order_obj.dict())
    
    # Clear cart after order
    await db.carts.update_one(
        {"user_id": current_user.id},
        {"$set": {"items": [], "total_amount": 0.0, "updated_at": datetime.utcnow()}}
    )
    
    return order_obj

@api_router.get("/orders", response_model=List[Order])
async def get_user_orders(current_user: User = Depends(get_current_user)):
    orders = await db.orders.find({"user_id": current_user.id}).to_list(100)
    return [Order(**order) for order in orders]

@api_router.get("/orders/{order_id}", response_model=Order)
async def get_order(order_id: str, current_user: User = Depends(get_current_user)):
    order = await db.orders.find_one({"id": order_id, "user_id": current_user.id})
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    return Order(**order)

# Initialize sample data
@api_router.post("/init-data")
async def initialize_sample_data():
    # Check if products already exist
    existing = await db.products.count_documents({})
    if existing > 0:
        return {"message": "Sample data already exists"}
    
    # Sample products with the images from vision_expert_agent
    sample_products = [
        # Hair Extensions
        {
            "name": "Premium Virgin Hair Extensions - 22 inch",
            "description": "100% virgin human hair extensions with natural shine and silky texture. Perfect for adding length and volume.",
            "price": 129.99,
            "category": "extensions",
            "subcategory": "clip_in",
            "images": ["https://images.unsplash.com/photo-1500917293891-ef795e70e1f6?crop=entropy&cs=srgb&fm=jpg&ixid=M3w3NDk1NzZ8MHwxfHNlYXJjaHwxfHxoYWlyJTIwZXh0ZW5zaW9uc3xlbnwwfHx8fDE3NTQ3ODM1NTB8MA&ixlib=rb-4.1.0&q=85"],
            "attributes": {"length": "22 inches", "color": "Natural Black", "texture": "Straight", "weight": "120g"},
            "stock_quantity": 50
        },
        {
            "name": "Curly Hair Extensions Bundle",
            "description": "Beautiful curly hair extensions for natural volume and bounce. Easy to style and maintain.",
            "price": 149.99,
            "category": "extensions",
            "subcategory": "sewn_in",
            "images": ["https://images.unsplash.com/photo-1634449571017-5fecfd26ad76?crop=entropy&cs=srgb&fm=jpg&ixid=M3w3NDk1NzZ8MHwxfHNlYXJjaHwyfHxoYWlyJTIwZXh0ZW5zaW9uc3xlbnwwfHx8fDE3NTQ3ODM1NTB8MA&ixlib=rb-4.1.0&q=85"],
            "attributes": {"length": "18 inches", "color": "Dark Brown", "texture": "Curly", "weight": "140g"},
            "stock_quantity": 35
        },
        # Wigs
        {
            "name": "Lace Front Wig - Natural Look",
            "description": "Premium lace front wig with natural hairline. Comfortable cap construction for all-day wear.",
            "price": 199.99,
            "category": "wigs",
            "subcategory": "lace_front",
            "images": ["https://images.unsplash.com/photo-1624489173879-7cc62610ddea?crop=entropy&cs=srgb&fm=jpg&ixid=M3w3NDk1Nzl8MHwxfHNlYXJjaHwxfHx3aWdzfGVufDB8fHx8MTc1NDc4MzU1NXww&ixlib=rb-4.1.0&q=85"],
            "attributes": {"length": "16 inches", "color": "Medium Brown", "texture": "Wavy", "cap_size": "Medium"},
            "stock_quantity": 25
        },
        {
            "name": "Colorful Wig Collection",
            "description": "Fun and vibrant colored wigs perfect for special occasions or daily wear.",
            "price": 89.99,
            "category": "wigs",
            "subcategory": "synthetic",
            "images": ["https://images.unsplash.com/photo-1634315775834-3e1ac73de6b6?crop=entropy&cs=srgb&fm=jpg&ixid=M3w3NDk1Nzl8MHwxfHNlYXJjaHwyfHx3aWdzfGVufDB8fHx8MTc1NDc4MzU1NXww&ixlib=rb-4.1.0&q=85"],
            "attributes": {"length": "12 inches", "color": "Various", "texture": "Straight", "cap_size": "One Size"},
            "stock_quantity": 40
        },
        # Hair Bundles
        {
            "name": "Brazilian Hair Bundle - 3 Pack",
            "description": "Premium Brazilian virgin hair bundles. Soft, silky and tangle-free.",
            "price": 299.99,
            "category": "bundles",
            "subcategory": "brazilian",
            "images": ["https://images.pexels.com/photos/6923472/pexels-photo-6923472.jpeg"],
            "attributes": {"length": "16-18-20 inches", "color": "Natural Black", "texture": "Body Wave", "pieces": "3 bundles"},
            "stock_quantity": 20
        },
        {
            "name": "Peruvian Hair Bundle Set",
            "description": "High-quality Peruvian hair bundles with natural shine and body.",
            "price": 279.99,
            "category": "bundles",
            "subcategory": "peruvian",
            "images": ["https://images.pexels.com/photos/6923557/pexels-photo-6923557.jpeg"],
            "attributes": {"length": "14-16-18 inches", "color": "Dark Brown", "texture": "Straight", "pieces": "3 bundles"},
            "stock_quantity": 15
        },
        # Hair Care Products
        {
            "name": "Hair Care Essentials Kit",
            "description": "Complete hair care kit with shampoo, conditioner, and styling tools.",
            "price": 49.99,
            "category": "hair_care",
            "subcategory": "shampoo_conditioner",
            "images": ["https://images.unsplash.com/photo-1717160675489-7779f2c91999?crop=entropy&cs=srgb&fm=jpg&ixid=M3w3NDk1Nzh8MHwxfHNlYXJjaHwxfHxoYWlyJTIwY2FyZXxlbnwwfHx8fDE3NTQ3ODM1NjV8MA&ixlib=rb-4.1.0&q=85"],
            "attributes": {"type": "Complete Kit", "size": "Set of 4", "scent": "Coconut"},
            "stock_quantity": 60
        },
        # Accessories
        {
            "name": "Professional Hair Tools Set",
            "description": "Complete set of professional hair styling tools including brushes, clips, and combs.",
            "price": 39.99,
            "category": "accessories",
            "subcategory": "tools",
            "images": ["https://images.pexels.com/photos/973401/pexels-photo-973401.jpeg"],
            "attributes": {"pieces": "15-piece set", "material": "Professional Grade", "color": "Black"},
            "stock_quantity": 45
        }
    ]
    
    # Insert products
    for product_data in sample_products:
        product_obj = Product(**product_data)
        await db.products.insert_one(product_obj.dict())
    
    return {"message": f"Initialized {len(sample_products)} sample products"}

# Include the router in the main app
app.include_router(api_router)

app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=os.environ.get('CORS_ORIGINS', '*').split(','),
    allow_methods=["*"],
    allow_headers=["*"],
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

@app.on_event("shutdown")
async def shutdown_db_client():
    client.close()