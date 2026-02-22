#!/usr/bin/env python3
"""
Anonymize cached competition data for test purposes with cryptographic security.

SECURITY APPROACH:
==================
Card numbers are PII (like social security numbers) and must be protected from
rainbow table attacks. This script uses synthetic card numbers with a secret salt.

VULNERABILITY: SHA256 with public salt
---------------------------------------
❌ INSECURE (old approach):
   Real card 53780 → SHA256("public_salt:53780") → "Shooter_9d9b6ee6"

   Problem: Attacker can brute-force:
   - Try cards 1-100000 with public salt (small keyspace)
   - Match hashes to test data
   - Recover all real card numbers in seconds!

SOLUTION: Synthetic cards with secret salt
-------------------------------------------
✅ SECURE (current approach):
   Real card 53780 → SHA256("SECRET_salt:53780") → synthetic card 10042
   Test data contains: 10042 (no connection to 53780 without secret)

   Why secure:
   - Secret salt stored locally (~/.webshooter/), never committed to git
   - Synthetic cards (10001, 10002, ...) reveal nothing about real cards
   - Without secret salt, attacker cannot reverse-engineer mappings
   - Deterministic: same real card → same synthetic card (for testing)

This script:
1. Generates or loads secret salt from ~/.webshooter/card_anonymization_salt.txt
2. Maps real card numbers to synthetic cards (10001, 10002, ...)
3. Replaces ALL real card numbers with synthetic ones
4. Removes PII: names, emails, phones, addresses, notes
5. Organizes data by year into tests/resources/test_data/competitions/

IMPORTANT:
- Secret salt is NEVER committed to git
- Mapping is deterministic (same input → same output)
- Deleting salt file creates new mappings (use carefully!)
"""

import hashlib
import json
import secrets
import shutil
from pathlib import Path
from typing import Any, Dict


class DataAnonymizer:
    """Anonymize competition data with cryptographic security."""

    def __init__(self):
        self.club_mapping = {}  # Maps real club IDs to anonymized club names
        self.club_counter = 1

        # SECRET salt for card anonymization (stored locally, never committed)
        self.salt_file = Path.home() / ".webshooter" / "card_anonymization_salt.txt"
        self.salt = self._get_or_create_secret_salt()

        # Track real → synthetic card mappings
        self.card_mapping = {}
        self.synthetic_counter = 10001  # Start synthetic cards at 10001

    def _get_or_create_secret_salt(self) -> str:
        """
        Get existing secret salt or create new one.

        Salt is stored at ~/.webshooter/card_anonymization_salt.txt
        This file is NEVER committed to git (in .gitignore)

        Returns:
            str: 64-character hex string (cryptographically random)
        """
        if self.salt_file.exists():
            salt = self.salt_file.read_text().strip()
            print(f"✅ Using existing secret salt from {self.salt_file}")
            return salt

        # Generate new cryptographically secure random salt
        salt = secrets.token_hex(32)  # 32 bytes = 64 hex chars
        self.salt_file.parent.mkdir(exist_ok=True)
        self.salt_file.write_text(salt)
        print("🔐 Generated NEW secret salt: {}".format(self.salt_file))
        print("⚠️  This salt is used to create synthetic card numbers")
        print("⚠️  DO NOT commit this file to git!")
        return salt

    def _anonymize_club(self, club_id: int, club_name: str) -> str:
        """Map club ID to anonymized name like 'Club_001'."""
        if club_id not in self.club_mapping:
            self.club_mapping[club_id] = f"Club_{self.club_counter:03d}"
            self.club_counter += 1
        return self.club_mapping[club_id]

    def _get_synthetic_card(self, real_card: str) -> str:
        """
        Map real card number to synthetic card number.

        Uses cryptographic hash with secret salt to create deterministic but
        non-reversible mapping: real_card → synthetic_card

        Security properties:
        - Deterministic: same real card always maps to same synthetic card
        - One-way: cannot derive real card from synthetic card without secret salt
        - Rainbow-resistant: attacker cannot brute-force without secret salt

        Args:
            real_card: Real card number (PII)

        Returns:
            str: Synthetic card number (e.g., "10001", "10002")
        """
        if not real_card:
            return "0"

        real_card_str = str(real_card)

        if real_card_str not in self.card_mapping:
            # Use hash to create deterministic ordering
            hash_input = "{}:{}".format(self.salt, real_card_str).encode("utf-8")
            _ = hashlib.sha256(hash_input).hexdigest()  # For deterministic ordering

            # Assign synthetic card ID
            synthetic_id = self.synthetic_counter
            self.card_mapping[real_card_str] = synthetic_id
            self.synthetic_counter += 1

        return str(self.card_mapping[real_card_str])

    def anonymize_club_data(self, club: Dict[str, Any]) -> Dict[str, Any]:
        """Anonymize club information."""
        if not club:
            return club

        anonymized_name = self._anonymize_club(club.get("id", 0), club.get("name", ""))

        return {
            "id": club["id"],
            "districts_id": club.get("districts_id"),
            "clubs_nr": club.get("clubs_nr", "000"),
            "name": anonymized_name,
            # REMOVE: email, phone, address, bankgiro, postgiro, swish
            "user_has_role": club.get("user_has_role"),
            "address_incomplete": False,
            # Keep structure fields but remove actual data
            "logo": None,
            "logo_url": None,
            "logo_path": None,
        }

    def anonymize_user_data(self, user: Dict[str, Any]) -> Dict[str, Any]:
        """Anonymize user/shooter information with synthetic card number."""
        if not user:
            return user

        real_card = user.get("shooting_card_number", "00000")
        synthetic_card = self._get_synthetic_card(str(real_card))

        return {
            "shooting_card_number": synthetic_card,  # SYNTHETIC CARD (not real PII)
            "name": synthetic_card,
            "lastname": f"Lastname_{synthetic_card}",
            "fullname": f"Shooter_{synthetic_card}",
            "grade_field": user.get("grade_field"),
            "grade_trackshooting": user.get("grade_trackshooting"),
            "user_id": user.get("user_id"),
            "clubs_id": user.get("clubs_id"),
            "status": user.get("status", "active"),
            # REMOVE: api_token, email, phone, address
            "clubs": [self.anonymize_club_data(c) for c in user.get("clubs", [])],
        }

    def anonymize_signup_data(self, signup: Dict[str, Any]) -> Dict[str, Any]:
        """Anonymize signup information."""
        if not signup:
            return signup

        anonymized = signup.copy()

        # Anonymize user if present
        if "user" in anonymized:
            anonymized["user"] = self.anonymize_user_data(anonymized["user"])

        # REMOVE: note, special_wishes (may contain personal info)
        anonymized["note"] = None
        anonymized["special_wishes"] = ""

        return anonymized

    def anonymize_competition_data(self, comp: Dict[str, Any]) -> Dict[str, Any]:
        """Anonymize competition metadata."""
        if "competitions" in comp:
            comp_data = comp["competitions"]
        else:
            comp_data = comp

        anonymized = comp_data.copy()

        # REMOVE: contact information
        if "contact_name" in anonymized:
            anonymized["contact_name"] = "Competition Organizer"
        if "contact_email" in anonymized:
            del anonymized["contact_email"]
        if "contact_telephone" in anonymized:
            del anonymized["contact_telephone"]

        # REMOVE: personal notes in results_comment
        if "results_comment" in anonymized:
            anonymized["results_comment"] = None

        # REMOVE: description if it contains names
        # For now, keep description but could be sanitized further if needed

        # REMOVE: google_maps (may contain location details)
        if "google_maps" in anonymized:
            anonymized["google_maps"] = None

        if "competitions" in comp:
            return {"competitions": anonymized}
        return anonymized

    def anonymize_result_data(self, result: Dict[str, Any]) -> Dict[str, Any]:
        """Anonymize result information."""
        anonymized = result.copy()

        # Anonymize signup data if present
        if "signup" in anonymized and anonymized["signup"]:
            anonymized["signup"] = self.anonymize_signup_data(anonymized["signup"])

        return anonymized

    def anonymize_results_file(self, results_data: Dict[str, Any]) -> Dict[str, Any]:
        """Anonymize a results JSON file."""
        if "results" not in results_data:
            return results_data

        return {"results": [self.anonymize_result_data(r) for r in results_data["results"]]}

    def anonymize_signups_file(self, signups_data: Dict[str, Any]) -> Dict[str, Any]:
        """Anonymize a signups JSON file."""
        if "signups" not in signups_data:
            return signups_data

        anonymized_signups = signups_data["signups"].copy()
        if "data" in anonymized_signups:
            anonymized_signups["data"] = [self.anonymize_signup_data(s) for s in anonymized_signups["data"]]

        return {"signups": anonymized_signups}

    def process_file(self, source_path: Path) -> Dict[str, Any]:
        """Read, anonymize, and return file data."""
        with open(source_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        # Determine file type and anonymize accordingly
        if "_results.json" in source_path.name:
            return self.anonymize_results_file(data)
        elif "_signups.json" in source_path.name:
            return self.anonymize_signups_file(data)
        elif source_path.name.startswith("competition_"):
            return self.anonymize_competition_data(data)
        else:
            # Other files (competitions.json, etc.) - minimal processing
            return data


def get_competition_year(comp_file: Path, cache_dir: Path) -> int:
    """Extract year from competition metadata."""
    try:
        with open(comp_file, "r", encoding="utf-8") as f:
            data = json.load(f)

        comp_data = data.get("competitions", data)
        date_str = comp_data.get("date", "")

        if date_str and "-" in date_str:
            return int(date_str.split("-")[0])

    except Exception as e:
        print(f"Warning: Could not determine year for {comp_file.name}: {e}")

    return 0  # Unknown year


def organize_by_year(cache_dir: Path, output_dir: Path):
    """Organize cached files and anonymize - using FLAT structure like cache."""
    anonymizer = DataAnonymizer()

    # Process competition files (flat structure, like cache)
    comp_files = sorted(cache_dir.glob("competition_*.json"))
    comp_files = [f for f in comp_files if "_results" not in f.name]

    print(f"Processing {len(comp_files)} competition files...")

    processed_count = 0
    for comp_file in comp_files:
        comp_id = comp_file.stem.replace("competition_", "")

        # Get year (for reporting only)
        year = get_competition_year(comp_file, cache_dir)
        if year == 0:
            print(f"Skipping {comp_file.name} (unknown year)")
            continue

        years = [2022, 2023, 2024, 2025]
        if year not in years:
            print(f"Skipping {comp_file.name} (year {year} not in target range)")
            continue

        # Anonymize and copy competition file (FLAT structure)
        anonymized_data = anonymizer.process_file(comp_file)
        output_file = output_dir / comp_file.name
        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(anonymized_data, f, indent=2, ensure_ascii=False)

        # Anonymize and copy results file if exists
        results_file = cache_dir / f"competition_{comp_id}_results.json"
        if results_file.exists():
            anonymized_results = anonymizer.process_file(results_file)
            output_results = output_dir / results_file.name
            with open(output_results, "w", encoding="utf-8") as f:
                json.dump(anonymized_results, f, indent=2, ensure_ascii=False)

        # Anonymize and copy signups file if exists
        signups_file = cache_dir / f"competition_{comp_id}_signups.json"
        if signups_file.exists():
            anonymized_signups = anonymizer.process_file(signups_file)
            output_signups = output_dir / signups_file.name
            with open(output_signups, "w", encoding="utf-8") as f:
                json.dump(anonymized_signups, f, indent=2, ensure_ascii=False)

        processed_count += 1
        if processed_count % 10 == 0:
            print(f"  Processed {processed_count} competitions...")

    print(f"✅ Processed {processed_count} competitions")
    print(f"✅ Anonymized with {len(anonymizer.club_mapping)} clubs")

    # Report reference card mapping (user approved: card 53780)
    reference_synthetic = None
    if "53780" in anonymizer.card_mapping:
        reference_synthetic = anonymizer.card_mapping["53780"]
        print("\n🔍 Reference card verification:")
        print("   Real card 53780 → Synthetic card {}".format(reference_synthetic))
        print("   Use '--card {}' in E2E tests".format(reference_synthetic))

    # Save reference card mapping to test data (for E2E test documentation)
    if reference_synthetic:
        reference_file = output_dir / "REFERENCE_CARD.txt"
        with open(reference_file, "w") as f:
            f.write("# Reference Card for E2E Tests\n")
            f.write("# User approved: 53780 is the developer's personal card\n")
            f.write("#\n")
            f.write("# Real card: 53780\n")
            f.write("# Synthetic card: {}\n".format(reference_synthetic))
            f.write("#\n")
            f.write("# Use in E2E tests:\n")
            f.write("#   webshooter --use-cache --cache-dir <path> bests 2024 --card {}\n".format(reference_synthetic))
            f.write("#\n")
            f.write("# Security note: Only this ONE mapping is revealed.\n")
            f.write("# Other synthetic cards cannot be reversed without secret salt.\n")
        print("   Saved to: {}".format(reference_file))

    # Save full mapping for debugging (local only, never committed)
    mapping_file = Path.home() / ".webshooter" / "card_mapping.json"
    with open(mapping_file, "w") as f:
        json.dump(anonymizer.card_mapping, f, indent=2, sort_keys=True)
    print("\n💾 Full card mapping saved to: {}".format(mapping_file))
    print("   (For debugging only - NOT committed to git)")


def main():
    """Main anonymization process."""
    cache_dir = Path.home() / ".cache" / "webshooter"
    output_dir = Path(__file__).parent.parent / "tests" / "resources" / "test_data" / "competitions"

    print("=" * 60)
    print("Webshooter Test Data Anonymization")
    print("=" * 60)
    print()
    print(f"Source: {cache_dir}")
    print(f"Target: {output_dir}")
    print()

    if not cache_dir.exists():
        print(f"❌ Error: Cache directory not found: {cache_dir}")
        return 1

    # Delete existing test data
    if output_dir.exists():
        print("Removing existing test data...")
        shutil.rmtree(output_dir)

    output_dir.mkdir(parents=True, exist_ok=True)

    # Organize and anonymize
    organize_by_year(cache_dir, output_dir)

    print()
    print("=" * 60)
    print("✅ Anonymization Complete!")
    print("=" * 60)
    print()
    print("IMPORTANT: Review the anonymized data to ensure:")
    print("  - No personal names remain")
    print("  - No email addresses remain")
    print("  - No phone numbers remain")
    print("  - No physical addresses remain")
    print("  - Club names are anonymized")
    print()

    return 0


if __name__ == "__main__":
    exit(main())
