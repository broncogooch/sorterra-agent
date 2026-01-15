import os
from pathlib import Path

def create_mock_files():
    test_dir = Path("./data/test_folder")
    test_dir.mkdir(exist_ok=True)

    # 1. An Invoice (should go to Finance/Invoices)
    with open(test_dir / "invoice_1024.txt", "w") as f:
        f.write("INVOICE #1024\nVendor: AWS\nTotal: $150.00\nDate: 2025-12-01\nDescription: Cloud hosting services.")

    # 2. Project Alpha Document (should go to Projects/Project Alpha)
    with open(test_dir / "alpha_plan.txt", "w") as f:
        f.write("Project Alpha: Phase 1 Specifications.\nThis document outlines the architecture for the Alpha initiative. Main goals: scalability and security.")

    # 3. Project Beta Document (should go to Projects/Project Beta)
    with open(test_dir / "beta_notes.txt", "w") as f:
        f.write("Notes from the Project Beta kickoff meeting. Discussing timeline and stakeholder requirements for the Beta release.")

    # 4. Ambiguous File (for testing Vector Memory)
    with open(test_dir / "vague_doc.txt", "w") as f:
        f.write("This is a technical document about cloud infrastructure. It doesn't mention a project name specifically, but it looks like an invoice or a plan.")

    # 5. Unsorted File (should go to Unsorted)
    with open(test_dir / "grocery_list.txt", "w") as f:
        f.write("Milk, Eggs, Bread, Coffee beans.")

    print(f"Created {len(list(test_dir.iterdir()))} mock files in {test_dir}")

if __name__ == "__main__":
    create_mock_files()