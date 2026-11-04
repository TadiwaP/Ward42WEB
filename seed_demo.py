

from datetime import timedelta

from app import app
from models import Report, db, now_utc

# category, street, description, status, name, cell, days ago
DEMO_REPORTS = [
    ("Pothole", "14 Tsamaya Road, next to the spaza shop", "Deep pothole in the middle of the road. Cars swerve to avoid it.", "Open", "Thandi Nkosi", "0710000001", 1),
    ("Water leak", "Corner of Mabuza Street and Sefako Drive", "Burst pipe. Water has been running down the street since Monday.", "In progress", "Sipho Dlamini", "0710000002", 2),
    ("Streetlight", "7 Moloto Road, opposite the creche", "The streetlight has been out for two weeks. It is very dark at night.", "Open", "Lerato Mokoena", "0710000003", 3),
    ("Illegal dumping", "Open field behind the community hall", "Building rubble and old mattresses dumped in the field.", "Open", "Johan Pretorius", "0710000004", 4),
    ("Pothole", "Bus stop on Hans Strijdom Drive", "Large hole at the bus stop where people wait for the taxi.", "Closed", "Nomsa Khumalo", "0710000005", 6),
    ("Water leak", "22 Mamelodi Crescent", "Water leaking from the meter box into the yard next door.", "Closed", "Peter Maseko", "0710000006", 7),
    ("Streetlight", "Football field entrance", "Two lights at the football field are broken. Children play there.", "In progress", "Zanele Mahlangu", "0710000007", 8),
    ("Other", "Primary school gate, Ndlovu Street", "The speed hump has worn away and cars drive fast past the school.", "Open", "Abel Radebe", "0710000008", 9),
    ("Illegal dumping", "Stream next to Phase 3", "Rubbish bags are blocking the stream and it smells bad.", "In progress", "Mpho Sithole", "0710000009", 10),
    ("Pothole", "Entrance to the clinic", "Pothole filled with water. Wheelchair users cannot get past.", "Closed", "Grace Tau", "0710000010", 12),
]

with app.app_context():
    for category, street, description, status, name, cell, days_ago in DEMO_REPORTS:
        report = Report(
            category=category,
            street=street,
            description=description,
            reporter_name=name,
            reporter_cell=cell,
            status=status,
            created_at=now_utc() - timedelta(days=days_ago, hours=days_ago),
        )
        db.session.add(report)
        db.session.flush()          # gives the report its id
        report.assign_reference()   # then W42-0001, W42-0002, ...
    db.session.commit()
    print("Added", len(DEMO_REPORTS), "demo reports. The database now has", Report.query.count(), "reports.")