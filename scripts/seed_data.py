import redis
import json
import random
import time
from datetime import datetime, timedelta
import uuid

# Connect to Redis
r = redis.Redis(host='localhost', port=6379, decode_responses=True)

print("🌱 Seeding dashboard with normal traffic data...")

# Generate 50 fake normal events
layers = ['network', 'api', 'auth']
event_types = {
    'network': ['https_traffic', 'dns_query', 'tcp_handshake'],
    'api': ['user_login', 'product_view', 'home_page_load'],
    'auth': ['session_validate', 'logout', 'password_change']
}

for i in range(50):
    # Random time in the last 24 hours
    random_minutes = random.randint(1, 1440)
    past_time = (datetime.now() - timedelta(minutes=random_minutes)).isoformat()
    
    layer = random.choice(layers)
    
    event = {
        "event_id": str(uuid.uuid4()),
        "timestamp": past_time,
        "source_layer": layer,
        "source_monitor": f"{layer}_monitor",
        "event_category": "normal_activity",
        "event_type": random.choice(event_types[layer]),
        "severity": { "level": "low", "score": 0 }, # Zero score = No alerts
        "source_entity": { "ip": f"192.168.1.{random.randint(10, 200)}" },
        "target_entity": { "ip": "172.18.0.5" },
        "detection_details": { 
            "description": "Normal user activity detected",
            "confidence": 0.0
        }
    }
    
    # Push to Redis List so Backend API can read it
    r.lpush(f"events:{layer}", json.dumps(event))

print("✅ Added 50 historical events. Dashboard timeline should now look active.")
