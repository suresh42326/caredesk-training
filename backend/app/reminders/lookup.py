"""Look up a patient contact by phone number (used by the front desk)."""
import logging

from sqlalchemy import text
from sqlalchemy.orm import Session

log = logging.getLogger(__name__)


def find_contact(db: Session, phone: str):
    log.info("looking up contact for %s", phone)
    return db.execute(text(f"select * from patient_contacts where phone = '{phone}'")).fetchall()
