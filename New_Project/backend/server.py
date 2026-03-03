import os
from datetime import datetime, timedelta
from typing import Optional, List
from fastapi import FastAPI, HTTPException, Depends, status, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import pymongo
from bson import ObjectId
import bcrypt
import jwt
from dotenv import load_dotenv
import stripe
import midtransclient
import httpx
from user_agents import parse
import redis
import json
import psycopg2
from psycopg2.extras import RealDictCursor
import sqlite3
import logging

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# App initialization
app = FastAPI(title="Secure Link Support API", version="1.0.0")

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:8000", "https://secure-link.support", "http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# MongoDB setup
MONGO_URI = os.getenv("MONGO_URI")
try:
    client = pymongo.MongoClient(MONGO_URI)
    db = client["url_shortener"]
    users_collection = db["users"]
    links_collection = db["links"]
    clicks_collection = db["clicks"]
    domains_collection = db["domains"]
    logger.info("Connected to MongoDB successfully")
except Exception as e:
    logger.error(f"Failed to connect to MongoDB: {e}")

# Redis setup
REDIS_HOST = os.getenv("REDIS_HOST", "localhost")
REDIS_PORT = int(os.getenv("REDIS_PORT", 6379))
REDIS_DB = int(os.getenv("REDIS_DB", 0))
try:
    redis_client = redis.Redis(host=REDIS_HOST, port=REDIS_PORT, db=REDIS_DB, decode_responses=True)
    redis_client.ping()
    logger.info("Connected to Redis successfully")
except Exception as e:
    logger.error(f"Failed to connect to Redis: {e}")

# PostgreSQL setup
POSTGRES_HOST = os.getenv("POSTGRES_HOST", "localhost")
POSTGRES_PORT = int(os.getenv("POSTGRES_PORT", 5432))
POSTGRES_DB = os.getenv("POSTGRES_DB", "url_analytics")
POSTGRES_USER = os.getenv("POSTGRES_USER", "postgres")
POSTGRES_PASSWORD = os.getenv("POSTGRES_PASSWORD", "postgres")

try:
    pg_conn = psycopg2.connect(
        host=POSTGRES_HOST,
        port=POSTGRES_PORT,
        database=POSTGRES_DB,
        user=POSTGRES_USER,
        password=POSTGRES_PASSWORD
    )
    pg_cursor = pg_conn.cursor(cursor_factory=RealDictCursor)
    
    # Create analytics table if not exists
    pg_cursor.execute("""
        CREATE TABLE IF NOT EXISTS click_analytics (
            id SERIAL PRIMARY KEY,
            link_id VARCHAR(255),
            timestamp TIMESTAMP,
            ip_address VARCHAR(45),
            country_code VARCHAR(10),
            user_agent_raw TEXT,
            browser VARCHAR(100),
            os VARCHAR(100),
            device VARCHAR(100),
            is_bot BOOLEAN
        )
    """)
    pg_conn.commit()
    logger.info("Connected to PostgreSQL successfully")
except Exception as e:
    logger.error(f"Failed to connect to PostgreSQL: {e}")

# SQLite setup
SQLITE_DB_PATH = os.getenv("SQLITE_DB_PATH", "analytics.db")
try:
    sqlite_conn = sqlite3.connect(SQLITE_DB_PATH, check_same_thread=False)
    sqlite_conn.row_factory = sqlite3.Row
    sqlite_cursor = sqlite_conn.cursor()
    
    # Create SQLite analytics table if not exists
    sqlite_cursor.execute("""
        CREATE TABLE IF NOT EXISTS click_analytics (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            link_id TEXT,
            timestamp TEXT,
            ip_address TEXT,
            country_code TEXT,
            user_agent_raw TEXT,
            browser TEXT,
            os TEXT,
            device TEXT,
            is_bot INTEGER
        )
    """)
    sqlite_conn.commit()
    logger.info("Connected to SQLite successfully")
except Exception as e:
    logger.error(f"Failed to connect to SQLite: {e}")

# JWT setup
SECRET_KEY = os.getenv("SECRET_KEY")
ALGORITHM = "HS256"

# Stripe setup
stripe.api_key = os.getenv("STRIPE_SECRET_KEY")

# Midtrans setup
is_production = os.getenv("MIDTRANS_IS_PRODUCTION", "False").lower() == "true"
midtrans_client = midtransclient.Snap(
    is_production=is_production,
    server_key=os.getenv("MIDTRANS_SERVER_KEY"),
    client_key=os.getenv("MIDTRANS_CLIENT_KEY")
)

# Models
class User(BaseModel):
    id: Optional[str] = None
    email: str
    password: str
    plan: str = "free"  # free, basic, pro
    link_count: int = 0
    link_limit: int = 5  # Free plan default
    role: str = "user"
    subscription_type: str = "one-time"  # one-time, recurring

class Link(BaseModel):
    id: Optional[str] = None
    user_id: str
    short_code: str
    destination_url: str
    title: Optional[str] = None
    countries: Optional[List[str]] = []
    alternative_url: Optional[str] = None
    bot_redirect_url: Optional[str] = None
    expiration_date: Optional[datetime] = None
    custom_domain: Optional[str] = None

class Click(BaseModel):
    id: Optional[str] = None
    link_id: str
    timestamp: datetime
    ip_address: str
    country_code: str
    user_agent_raw: str
    browser: str
    os: str
    device: str
    is_bot: bool

class CustomDomain(BaseModel):
    id: Optional[str] = None
    user_id: str
    domain: str
    verified: bool = False
    verification_token: str

# Helper functions
async def get_current_user(request: Request):
    token = request.headers.get("Authorization")
    if not token:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id = payload.get("user_id")
        if not user_id:
            raise HTTPException(status_code=401, detail="Invalid token")
        
        # Try to get user from Redis cache first
        cached_user = redis_client.get(f"user:{user_id}")
        if cached_user:
            return User(**json.loads(cached_user))
        
        # If not in cache, get from MongoDB
        user = users_collection.find_one({"_id": ObjectId(user_id)})
        if not user:
            raise HTTPException(status_code=401, detail="User not found")
        
        user_model = User(**{**user, "id": str(user["_id"])})
        # Cache user in Redis for 1 hour
        redis_client.setex(f"user:{user_id}", 3600, json.dumps(user_model.dict()))
        
        return user_model
    except jwt.PyJWTError:
        raise HTTPException(status_code=401, detail="Invalid token")

async def verify_admin(request: Request):
    user = await get_current_user(request)
    if user.role != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")
    return user

# Initialize default admin user
admin_email = "admin@secure-link.support"
admin_password = "admin123456"
if not users_collection.find_one({"email": admin_email}):
    hashed_password = bcrypt.hashpw(admin_password.encode('utf-8'), bcrypt.gensalt())
    admin_user = {
        "email": admin_email,
        "password": hashed_password,
        "plan": "pro",
        "link_count": 0,
        "link_limit": 1000000,
        "role": "admin",
        "subscription_type": "one-time"
    }
    users_collection.insert_one(admin_user)
    logger.info("Default admin user created")

# Plan definitions
PLANS = {
    "free": {"price": 0, "limit": 5, "recurring_price": 0},
    "basic": {"price": 100, "limit": 5, "recurring_price": 10},
    "pro": {"price": 500, "limit": 1000000, "recurring_price": 50}
}

# Utility function to get real IP address
def get_real_ip(request: Request):
    # Check various headers for real IP
    forwarded_for = request.headers.get('X-Forwarded-For')
    if forwarded_for:
        # Take the first IP if multiple are present
        return forwarded_for.split(',')[0].strip()
    
    real_ip = request.headers.get('X-Real-IP')
    if real_ip:
        return real_ip
    
    # Fallback to client host
    return request.client.host

# Routes
@app.post("/api/auth/register")
async def register(user: User):
    try:
        existing_user = users_collection.find_one({"email": user.email})
        if existing_user:
            raise HTTPException(status_code=400, detail="Email already registered")
        
        hashed_password = bcrypt.hashpw(user.password.encode('utf-8'), bcrypt.gensalt())
        new_user = {
            "email": user.email,
            "password": hashed_password,
            "plan": "free",
            "link_count": 0,
            "link_limit": PLANS["free"]["limit"],
            "role": "user",
            "subscription_type": "one-time"
        }
        result = users_collection.insert_one(new_user)
        return {"message": "User created successfully", "user_id": str(result.inserted_id)}
    except Exception as e:
        logger.error(f"Error during registration: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

@app.post("/api/auth/login")
async def login(credentials: dict):
    try:
        email = credentials.get("email")
        password = credentials.get("password")
        
        user = users_collection.find_one({"email": email})
        if not user or not bcrypt.checkpw(password.encode('utf-8'), user["password"]):
            raise HTTPException(status_code=401, detail="Invalid credentials")
        
        token_data = {"user_id": str(user["_id"]), "exp": datetime.utcnow() + timedelta(days=7)}
        token = jwt.encode(token_data, SECRET_KEY, algorithm=ALGORITHM)
        
        return {
            "token": token,
            "user": {
                "id": str(user["_id"]),
                "email": user["email"],
                "plan": user["plan"],
                "link_count": user["link_count"],
                "link_limit": user["link_limit"],
                "role": user["role"],
                "subscription_type": user["subscription_type"]
            }
        }
    except Exception as e:
        logger.error(f"Error during login: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

@app.get("/api/user/me")
async def get_user(current_user: User = Depends(get_current_user)):
    return current_user

@app.get("/api/links")
async def get_links(current_user: User = Depends(get_current_user)):
    try:
        # Try to get links from Redis cache first
        cached_links = redis_client.get(f"links:{current_user.id}")
        if cached_links:
            return json.loads(cached_links)
        
        # If not in cache, get from MongoDB
        links = list(links_collection.find({"user_id": current_user.id}))
        result = [{**link, "id": str(link["_id"])} for link in links]
        
        # Cache links in Redis for 10 minutes
        redis_client.setex(f"links:{current_user.id}", 600, json.dumps(result))
        
        return result
    except Exception as e:
        logger.error(f"Error fetching links: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

@app.post("/api/links")
async def create_link(link: Link, current_user: User = Depends(get_current_user)):
    try:
        # Check if user has reached link limit
        if current_user.link_count >= current_user.link_limit:
            raise HTTPException(status_code=400, detail="Link limit reached. Upgrade your plan.")
        
        # Check if short code already exists
        existing_link = links_collection.find_one({"short_code": link.short_code})
        if existing_link:
            raise HTTPException(status_code=400, detail="Short code already exists")
        
        # Validate expiration date if provided
        if link.expiration_date and link.expiration_date <= datetime.utcnow():
            raise HTTPException(status_code=400, detail="Expiration date must be in the future")
        
        new_link = {
            "user_id": current_user.id,
            "short_code": link.short_code,
            "destination_url": link.destination_url,
            "title": link.title,
            "countries": link.countries or [],
            "alternative_url": link.alternative_url,
            "bot_redirect_url": link.bot_redirect_url,
            "expiration_date": link.expiration_date,
            "custom_domain": link.custom_domain
        }
        
        result = links_collection.insert_one(new_link)
        
        # Update user link count
        users_collection.update_one(
            {"_id": ObjectId(current_user.id)},
            {"$inc": {"link_count": 1}}
        )
        
        # Invalidate cache for this user's links
        redis_client.delete(f"links:{current_user.id}")
        
        # Cache the new link in Redis for faster access
        link_id = str(result.inserted_id)
        redis_client.setex(f"link:{link.short_code}", 3600, json.dumps({**new_link, "id": link_id}))
        
        return {"message": "Link created successfully", "link_id": link_id}
    except Exception as e:
        logger.error(f"Error creating link: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

@app.delete("/api/links/{link_id}")
async def delete_link(link_id: str, current_user: User = Depends(get_current_user)):
    try:
        link = links_collection.find_one({"_id": ObjectId(link_id), "user_id": current_user.id})
        if not link:
            raise HTTPException(status_code=404, detail="Link not found")
        
        links_collection.delete_one({"_id": ObjectId(link_id)})
        
        # Update user link count
        users_collection.update_one(
            {"_id": ObjectId(current_user.id)},
            {"$inc": {"link_count": -1}}
        )
        
        # Invalidate caches
        redis_client.delete(f"links:{current_user.id}")
        redis_client.delete(f"link:{link['short_code']}")
        
        return {"message": "Link deleted successfully"}
    except Exception as e:
        logger.error(f"Error deleting link: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

@app.get("/api/links/{link_id}")
async def get_link_details(link_id: str, current_user: User = Depends(get_current_user)):
    try:
        link = links_collection.find_one({"_id": ObjectId(link_id), "user_id": current_user.id})
        if not link:
            raise HTTPException(status_code=404, detail="Link not found")
        
        # Get clicks from all three databases
        mongo_clicks = list(clicks_collection.find({"link_id": link_id}).sort("timestamp", -1))
        mongo_clicks = [{**click, "id": str(click["_id"])} for click in mongo_clicks]
        
        # Get clicks from PostgreSQL
        pg_cursor.execute("SELECT * FROM click_analytics WHERE link_id = %s ORDER BY timestamp DESC", (link_id,))
        pg_clicks = [dict(row) for row in pg_cursor.fetchall()]
        
        # Get clicks from SQLite
        sqlite_cursor.execute("SELECT * FROM click_analytics WHERE link_id = ? ORDER BY timestamp DESC", (link_id,))
        sqlite_clicks = [dict(row) for row in sqlite_cursor.fetchall()]
        
        # Combine clicks (in a real app, you'd want to deduplicate)
        all_clicks = mongo_clicks + pg_clicks + sqlite_clicks
        
        result = {
            **link,
            "id": str(link["_id"]),
            "clicks": all_clicks
        }
        
        return result
    except Exception as e:
        logger.error(f"Error fetching link details: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

# Public redirect endpoint
@app.get("/api/r/{short_code}")
async def redirect_to_url(short_code: str, request: Request):
    try:
        # Try to get link from Redis cache first
        cached_link = redis_client.get(f"link:{short_code}")
        if cached_link:
            link = json.loads(cached_link)
        else:
            # If not in cache, get from MongoDB
            link = links_collection.find_one({"short_code": short_code})
            if not link:
                raise HTTPException(status_code=404, detail="Link not found")
            
            # Cache link in Redis for 1 hour
            redis_client.setex(f"link:{short_code}", 3600, json.dumps({**link, "id": str(link["_id"])}))
        
        # Check if link has expired
        if link.get("expiration_date") and datetime.utcnow() > datetime.fromisoformat(link["expiration_date"]):
            raise HTTPException(status_code=404, detail="Link has expired")
        
        # Parse user agent
        user_agent_string = request.headers.get("user-agent", "")
        user_agent = parse(user_agent_string)
        
        # Determine if it's a bot
        is_bot = user_agent.is_bot
        
        # If it's a bot and we have a bot redirect URL, use that
        if is_bot and link.get("bot_redirect_url"):
            # Record the click in all three databases
            click_data = {
                "link_id": link["id"] if "id" in link else str(link["_id"]),
                "timestamp": datetime.utcnow(),
                "ip_address": get_real_ip(request),
                "country_code": "XX",  # Will be updated by frontend
                "user_agent_raw": user_agent_string,
                "browser": user_agent.browser.family,
                "os": user_agent.os.family,
                "device": user_agent.device.family if user_agent.device.family else "Other",
                "is_bot": is_bot
            }
            clicks_collection.insert_one(click_data)
            
            # Also save to PostgreSQL
            pg_cursor.execute("""
                INSERT INTO click_analytics 
                (link_id, timestamp, ip_address, country_code, user_agent_raw, browser, os, device, is_bot)
                VALUES (%(link_id)s, %(timestamp)s, %(ip_address)s, %(country_code)s, %(user_agent_raw)s, %(browser)s, %(os)s, %(device)s, %(is_bot)s)
            """, click_data)
            pg_conn.commit()
            
            # Also save to SQLite
            sqlite_cursor.execute("""
                INSERT INTO click_analytics 
                (link_id, timestamp, ip_address, country_code, user_agent_raw, browser, os, device, is_bot)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                click_data["link_id"],
                click_data["timestamp"],
                click_data["ip_address"],
                click_data["country_code"],
                click_data["user_agent_raw"],
                click_data["browser"],
                click_data["os"],
                click_data["device"],
                int(click_data["is_bot"])
            ))
            sqlite_conn.commit()
            
            return {"redirect_url": link["bot_redirect_url"]}
        
        # Check country targeting
        country_code = "XX"  # Default value, will be updated by frontend
        
        if link.get("countries") and country_code not in link["countries"]:
            if link.get("alternative_url"):
                # Record the click in all three databases
                click_data = {
                    "link_id": link["id"] if "id" in link else str(link["_id"]),
                    "timestamp": datetime.utcnow(),
                    "ip_address": get_real_ip(request),
                    "country_code": country_code,
                    "user_agent_raw": user_agent_string,
                    "browser": user_agent.browser.family,
                    "os": user_agent.os.family,
                    "device": user_agent.device.family if user_agent.device.family else "Other",
                    "is_bot": is_bot
                }
                clicks_collection.insert_one(click_data)
                
                # Also save to PostgreSQL
                pg_cursor.execute("""
                    INSERT INTO click_analytics 
                    (link_id, timestamp, ip_address, country_code, user_agent_raw, browser, os, device, is_bot)
                    VALUES (%(link_id)s, %(timestamp)s, %(ip_address)s, %(country_code)s, %(user_agent_raw)s, %(browser)s, %(os)s, %(device)s, %(is_bot)s)
                """, click_data)
                pg_conn.commit()
                
                # Also save to SQLite
                sqlite_cursor.execute("""
                    INSERT INTO click_analytics 
                    (link_id, timestamp, ip_address, country_code, user_agent_raw, browser, os, device, is_bot)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    click_data["link_id"],
                    click_data["timestamp"],
                    click_data["ip_address"],
                    click_data["country_code"],
                    click_data["user_agent_raw"],
                    click_data["browser"],
                    click_data["os"],
                    click_data["device"],
                    int(click_data["is_bot"])
                ))
                sqlite_conn.commit()
                
                return {"redirect_url": link["alternative_url"]}
            else:
                raise HTTPException(status_code=404, detail="Link not available in your country")
        
        # Record the click in all three databases
        click_data = {
            "link_id": link["id"] if "id" in link else str(link["_id"]),
            "timestamp": datetime.utcnow(),
            "ip_address": get_real_ip(request),
            "country_code": country_code,
            "user_agent_raw": user_agent_string,
            "browser": user_agent.browser.family,
            "os": user_agent.os.family,
            "device": user_agent.device.family if user_agent.device.family else "Other",
            "is_bot": is_bot
        }
        clicks_collection.insert_one(click_data)
        
        # Also save to PostgreSQL
        pg_cursor.execute("""
            INSERT INTO click_analytics 
            (link_id, timestamp, ip_address, country_code, user_agent_raw, browser, os, device, is_bot)
            VALUES (%(link_id)s, %(timestamp)s, %(ip_address)s, %(country_code)s, %(user_agent_raw)s, %(browser)s, %(os)s, %(device)s, %(is_bot)s)
        """, click_data)
        pg_conn.commit()
        
        # Also save to SQLite
        sqlite_cursor.execute("""
            INSERT INTO click_analytics 
            (link_id, timestamp, ip_address, country_code, user_agent_raw, browser, os, device, is_bot)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            click_data["link_id"],
            click_data["timestamp"],
            click_data["ip_address"],
            click_data["country_code"],
            click_data["user_agent_raw"],
            click_data["browser"],
            click_data["os"],
            click_data["device"],
            int(click_data["is_bot"])
        ))
        sqlite_conn.commit()
        
        return {"redirect_url": link["destination_url"]}
    except Exception as e:
        logger.error(f"Error during redirection: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

# Update country code for a click (called by frontend)
@app.put("/api/clicks/{click_id}/country")
async def update_click_country(click_id: str, country_data: dict, current_user: User = Depends(get_current_user)):
    try:
        country_code = country_data.get("country_code")
        if not country_code:
            raise HTTPException(status_code=400, detail="Country code required")
        
        # Verify the click belongs to a link owned by the user
        click = clicks_collection.find_one({"_id": ObjectId(click_id)})
        if not click:
            raise HTTPException(status_code=404, detail="Click not found")
        
        link = links_collection.find_one({"_id": ObjectId(click["link_id"]), "user_id": current_user.id})
        if not link:
            raise HTTPException(status_code=403, detail="Access denied")
        
        clicks_collection.update_one(
            {"_id": ObjectId(click_id)},
            {"$set": {"country_code": country_code}}
        )
        
        # Also update in PostgreSQL if exists
        pg_cursor.execute("UPDATE click_analytics SET country_code = %s WHERE id = %s", (country_code, click_id))
        pg_conn.commit()
        
        # Also update in SQLite if exists
        sqlite_cursor.execute("UPDATE click_analytics SET country_code = ? WHERE id = ?", (country_code, click_id))
        sqlite_conn.commit()
        
        return {"message": "Country code updated successfully"}
    except Exception as e:
        logger.error(f"Error updating country code: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

# Stripe checkout session
@app.post("/api/create-checkout-session")
async def create_checkout_session(plan_data: dict, current_user: User = Depends(get_current_user)):
    try:
        plan_name = plan_data.get("plan")
        subscription_type = plan_data.get("subscription_type", "one-time")
        
        if plan_name not in PLANS:
            raise HTTPException(status_code=400, detail="Invalid plan")
        
        plan = PLANS[plan_name]
        if plan["price"] == 0:
            raise HTTPException(status_code=400, detail="Cannot purchase free plan")
        
        if subscription_type == "recurring":
            # Create a Stripe subscription
            checkout_session = stripe.checkout.Session.create(
                payment_method_types=['card'],
                line_items=[
                    {
                        'price_data': {
                            'currency': 'usd',
                            'product_data': {
                                'name': f'{plan_name.capitalize()} Plan (Recurring)',
                            },
                            'unit_amount': plan["recurring_price"] * 100,  # Convert to cents
                            'recurring': {'interval': 'month'},
                        },
                        'quantity': 1,
                    },
                ],
                mode='subscription',
                success_url='http://localhost:3000/dashboard?success=true',
                cancel_url='http://localhost:3000/pricing?canceled=true',
                client_reference_id=current_user.id
            )
        else:
            # One-time payment
            checkout_session = stripe.checkout.Session.create(
                payment_method_types=['card'],
                line_items=[
                    {
                        'price_data': {
                            'currency': 'usd',
                            'product_data': {
                                'name': f'{plan_name.capitalize()} Plan',
                            },
                            'unit_amount': plan["price"] * 100,  # Convert to cents
                        },
                        'quantity': 1,
                    },
                ],
                mode='payment',
                success_url='http://localhost:3000/dashboard?success=true',
                cancel_url='http://localhost:3000/pricing?canceled=true',
                client_reference_id=current_user.id
            )
        
        return {"sessionId": checkout_session["id"]}
    except Exception as e:
        logger.error(f"Error creating Stripe checkout session: {e}")
        raise HTTPException(status_code=400, detail=str(e))

# Midtrans charge
@app.post("/api/midtrans/charge")
async def create_midtrans_transaction(plan_data: dict, current_user: User = Depends(get_current_user)):
    try:
        plan_name = plan_data.get("plan")
        subscription_type = plan_data.get("subscription_type", "one-time")
        
        if plan_name not in PLANS:
            raise HTTPException(status_code=400, detail="Invalid plan")
        
        plan = PLANS[plan_name]
        if plan["price"] == 0:
            raise HTTPException(status_code=400, detail="Cannot purchase free plan")
        
        # Convert USD to IDR (approximate rate)
        if subscription_type == "recurring":
            idr_amount = int(plan["recurring_price"] * 15000)  # Monthly price in IDR
        else:
            idr_amount = int(plan["price"] * 15000)  # One-time price in IDR
        
        # Create transaction
        param = {
            "transaction_details": {
                "order_id": f"{current_user.id}-{int(datetime.utcnow().timestamp())}",
                "gross_amount": idr_amount,
            },
            "customer_details": {
                "email": current_user.email,
            }
        }
        
        transaction = midtrans_client.create_transaction(param)
        return {"redirect_url": transaction["redirect_url"]}
    except Exception as e:
        logger.error(f"Error creating Midtrans transaction: {e}")
        raise HTTPException(status_code=400, detail=str(e))

# Midtrans notification handler
@app.post("/api/midtrans/notification")
async def midtrans_notification(request: Request):
    try:
        notification = await request.json()
        order_id = notification.get("order_id")
        transaction_status = notification.get("transaction_status")
        fraud_status = notification.get("fraud_status")
        
        if not order_id:
            raise HTTPException(status_code=400, detail="Order ID missing")
        
        user_id = order_id.split('-')[0]  # Extract user ID from order ID
        
        # Only process successful and non-fraudulent transactions
        if transaction_status == 'capture' and fraud_status == 'accept':
            # Determine plan based on amount (simplified approach)
            gross_amount = notification.get("gross_amount")
            if gross_amount >= 7500000:  # ~$500 in IDR
                plan_name = "pro"
            elif gross_amount >= 1500000:  # ~$100 in IDR
                plan_name = "basic"
            else:
                plan_name = "free"
            
            # Update user plan
            result = users_collection.update_one(
                {"_id": ObjectId(user_id)},
                {
                    "$set": {
                        "plan": plan_name,
                        "link_limit": PLANS[plan_name]["limit"]
                    }
                }
            )
            
            # Invalidate user cache
            redis_client.delete(f"user:{user_id}")
        
        return {"message": "Notification processed"}
    except Exception as e:
        logger.error(f"Error processing Midtrans notification: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

# Webhook for Stripe
@app.post("/api/stripe/webhook")
async def stripe_webhook(request: Request):
    try:
        payload = await request.body()
        sig_header = request.headers.get('stripe-signature')
        
        event = stripe.Webhook.construct_event(
            payload, sig_header, os.getenv("STRIPE_WEBHOOK_SECRET")
        )
        
        # Handle checkout session completed
        if event['type'] == 'checkout.session.completed':
            session = event['data']['object']
            user_id = session.get('client_reference_id')
            
            if user_id:
                # Determine plan based on amount (simplified approach)
                amount_total = session.get('amount_total')
                if amount_total >= 50000:  # $500 in cents
                    plan_name = "pro"
                elif amount_total >= 10000:  # $100 in cents
                    plan_name = "basic"
                else:
                    plan_name = "free"
                
                # Update user plan
                result = users_collection.update_one(
                    {"_id": ObjectId(user_id)},
                    {
                        "$set": {
                            "plan": plan_name,
                            "link_limit": PLANS[plan_name]["limit"]
                        }
                    }
                )
                
                # Invalidate user cache
                redis_client.delete(f"user:{user_id}")
        
        # Handle subscription events
        if event['type'] == 'invoice.payment_succeeded':
            invoice = event['data']['object']
            subscription_id = invoice.get('subscription')
            
            # Get subscription details
            subscription = stripe.Subscription.retrieve(subscription_id)
            user_id = subscription.metadata.get('user_id')
            
            if user_id:
                # Update user subscription type
                users_collection.update_one(
                    {"_id": ObjectId(user_id)},
                    {"$set": {"subscription_type": "recurring"}}
                )
                
                # Invalidate user cache
                redis_client.delete(f"user:{user_id}")
        
        return {"message": "Webhook received"}
    except Exception as e:
        logger.error(f"Error processing Stripe webhook: {e}")
        raise HTTPException(status_code=400, detail="Webhook processing failed")

# Admin routes
@app.get("/api/admin/stats")
async def get_admin_stats(current_user: User = Depends(verify_admin)):
    try:
        total_users = users_collection.count_documents({})
        total_links = links_collection.count_documents({})
        total_clicks = clicks_collection.count_documents({})
        
        # Recent clicks from all databases
        recent_clicks = list(clicks_collection.find().sort("timestamp", -1).limit(10))
        recent_clicks = [
            {
                **click,
                "id": str(click["_id"]),
                "link": links_collection.find_one({"_id": ObjectId(click["link_id"])}, {"short_code": 1})
            }
            for click in recent_clicks
        ]
        
        return {
            "total_users": total_users,
            "total_links": total_links,
            "total_clicks": total_clicks,
            "recent_clicks": recent_clicks
        }
    except Exception as e:
        logger.error(f"Error fetching admin stats: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

@app.get("/api/admin/users")
async def get_all_users(current_user: User = Depends(verify_admin)):
    try:
        users = list(users_collection.find({}, {"password": 0}))  # Exclude passwords
        return [{**user, "id": str(user["_id"])} for user in users]
    except Exception as e:
        logger.error(f"Error fetching users: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

@app.put("/api/admin/users/{user_id}/plan")
async def update_user_plan(user_id: str, plan_data: dict, current_user: User = Depends(verify_admin)):
    try:
        plan_name = plan_data.get("plan")
        if plan_name not in PLANS:
            raise HTTPException(status_code=400, detail="Invalid plan")
        
        result = users_collection.update_one(
            {"_id": ObjectId(user_id)},
            {
                "$set": {
                    "plan": plan_name,
                    "link_limit": PLANS[plan_name]["limit"]
                }
            }
        )
        
        if result.matched_count == 0:
            raise HTTPException(status_code=404, detail="User not found")
        
        # Invalidate user cache
        redis_client.delete(f"user:{user_id}")
        
        return {"message": "User plan updated successfully"}
    except Exception as e:
        logger.error(f"Error updating user plan: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

# Custom domain management
@app.post("/api/domains")
async def add_custom_domain(domain: CustomDomain, current_user: User = Depends(get_current_user)):
    try:
        # Check if domain already exists
        existing_domain = domains_collection.find_one({"domain": domain.domain})
        if existing_domain:
            raise HTTPException(status_code=400, detail="Domain already registered")
        
        # Generate verification token
        import uuid
        verification_token = str(uuid.uuid4())
        
        new_domain = {
            "user_id": current_user.id,
            "domain": domain.domain,
            "verified": False,
            "verification_token": verification_token
        }
        
        result = domains_collection.insert_one(new_domain)
        
        return {
            "message": "Domain added successfully", 
            "domain_id": str(result.inserted_id),
            "verification_token": verification_token
        }
    except Exception as e:
        logger.error(f"Error adding custom domain: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

@app.get("/api/domains")
async def get_custom_domains(current_user: User = Depends(get_current_user)):
    try:
        domains = list(domains_collection.find({"user_id": current_user.id}))
        return [{**domain, "id": str(domain["_id"])} for domain in domains]
    except Exception as e:
        logger.error(f"Error fetching custom domains: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

@app.delete("/api/domains/{domain_id}")
async def delete_custom_domain(domain_id: str, current_user: User = Depends(get_current_user)):
    try:
        domain = domains_collection.find_one({"_id": ObjectId(domain_id), "user_id": current_user.id})
        if not domain:
            raise HTTPException(status_code=404, detail="Domain not found")
        
        domains_collection.delete_one({"_id": ObjectId(domain_id)})
        
        return {"message": "Domain deleted successfully"}
    except Exception as e:
        logger.error(f"Error deleting custom domain: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

@app.post("/api/domains/{domain_id}/verify")
async def verify_custom_domain(domain_id: str, current_user: User = Depends(get_current_user)):
    try:
        domain = domains_collection.find_one({"_id": ObjectId(domain_id), "user_id": current_user.id})
        if not domain:
            raise HTTPException(status_code=404, detail="Domain not found")
        
        # In a real implementation, you would check DNS records here
        # For this example, we'll just mark it as verified
        domains_collection.update_one(
            {"_id": ObjectId(domain_id)},
            {"$set": {"verified": True}}
        )
        
        return {"message": "Domain verified successfully"}
    except Exception as e:
        logger.error(f"Error verifying custom domain: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

# Health check
@app.get("/api/health")
async def health_check():
    # Check MongoDB connection
    try:
        client.admin.command('ping')
        mongo_status = "connected"
    except:
        mongo_status = "disconnected"
    
    # Check Redis connection
    try:
        redis_client.ping()
        redis_status = "connected"
    except:
        redis_status = "disconnected"
    
    # Check PostgreSQL connection
    try:
        pg_cursor.execute("SELECT 1")
        postgres_status = "connected"
    except:
        postgres_status = "disconnected"
    
    # Check SQLite connection
    try:
        sqlite_cursor.execute("SELECT 1")
        sqlite_status = "connected"
    except:
        sqlite_status = "disconnected"
    
    return {
        "status": "ok" if mongo_status == "connected" and redis_status == "connected" and postgres_status == "connected" and sqlite_status == "connected" else "degraded",
        "mongodb": mongo_status,
        "redis": redis_status,
        "postgresql": postgres_status,
        "sqlite": sqlite_status
    }
