import os
import random
import string
from pathlib import Path
from datetime import datetime, timedelta

def get_random_id(length=4):
    """Generates a short random string to ensure unique filenames."""
    return ''.join(random.choices(string.ascii_lowercase + string.digits, k=length))

def get_random_date():
    start_date = datetime(2025, 1, 1)
    random_days = random.randint(0, 365)
    return (start_date + timedelta(days=random_days)).strftime("%Y-%m-%d")

def create_mock_files():
    test_dir = Path("./data/test_folder")
    test_dir.mkdir(exist_ok=True)

    # 1. Randomized Invoice Filename and Content
    vendors = ["AWS", "Google Cloud", "Azure", "Twilio", "Stripe", "GitHub"]
    vendor = random.choice(vendors)
    amount = f"{random.uniform(50.0, 500.0):.2f}"
    inv_id = random.randint(1000, 9999)
    # Filename includes a random ID to prevent collisions
    with open(test_dir / f"invoice_{inv_id}_{get_random_id()}.txt", "w") as f:
        f.write(f"INVOICE #{inv_id}\n"
                f"Vendor: {vendor}\n"
                f"Total: ${amount}\n"
                f"Date: {get_random_date()}\n"
                f"Description: Monthly subscription for {vendor} infrastructure services.")

    # 2. Randomized Project Alpha Filename
    alpha_tasks = ["UI Refactoring", "Database Migration", "API Authentication", "Load Balancing"]
    task = random.choice(alpha_tasks)
    with open(test_dir / f"alpha_plan_{get_random_id()}.txt", "w") as f:
        f.write(f"Project Alpha: {task} Phase.\n"
                f"This document focuses on the {task.lower()} requirements for the Alpha initiative. "
                f"Success criteria: system stability and reduced latency.")

    # 3. Randomized Project Beta Filename
    beta_updates = ["Stakeholder Feedback", "Sprint Retrospective", "Architecture Review", "Security Audit"]
    update_type = random.choice(beta_updates)
    with open(test_dir / f"beta_notes_{get_random_id()}.txt", "w") as f:
        f.write(f"Notes from the Project Beta {update_type}.\n"
                f"Discussion points included the {random.choice(['Q3 roadmap', 'deployment pipeline', 'user testing results'])}. "
                f"Assigned to the primary engineering lead.")

    # 4. Randomized Ambiguous Filename
    tech_topics = ["serverless functions", "container orchestration", "distributed logging", "edge computing"]
    topic = random.choice(tech_topics)
    with open(test_dir / f"vague_doc_{get_random_id()}.txt", "w") as f:
        f.write(f"Technical overview regarding {topic}.\n"
                f"This document explores the implementation of {topic} within our current cloud infrastructure. "
                f"It serves as a general reference for upcoming architectural decisions.")

    # 5. Randomized Unsorted Filename
    items = ["Milk", "Eggs", "Bread", "Coffee beans", "Apples", "Chicken breast", "Pasta", "Laundry detergent"]
    selected_items = random.sample(items, k=random.randint(3, 6))
    with open(test_dir / f"grocery_list_{get_random_id()}.txt", "w") as f:
        f.write(", ".join(selected_items) + ".")

    print(f"Created {len(list(test_dir.iterdir()))} unique mock files in {test_dir}")

if __name__ == "__main__":
    create_mock_files()