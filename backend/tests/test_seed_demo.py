from sqlalchemy import select


def test_seed_demo_idempotent():
    from app.db.base import SessionLocal
    from app.models.patients import Patient
    from app.models.users import User, UserRole
    from app.models.visits import Visit
    from scripts.seed_demo import seed_demo

    # 1. Run initial seed
    stats1 = seed_demo()
    assert stats1["users_seeded"] == 3
    assert stats1["patients_seeded"] == 6
    assert stats1["visits_seeded"] == 6

    # Verify accounts exist
    with SessionLocal() as db:
        doctor = db.scalar(select(User).where(User.email == "demo.doctor@example.com"))
        assert doctor is not None
        assert doctor.role == UserRole.doctor

        readonly = db.scalar(select(User).where(User.email == "demo.readonly@example.com"))
        assert readonly is not None
        assert readonly.role == UserRole.read_only

        admin = db.scalar(select(User).where(User.email == "demo.admin@example.com"))
        assert admin is not None
        assert admin.role == UserRole.admin

        patients = db.scalars(select(Patient).where(Patient.full_name.like("Demo Patient%"))).all()
        assert len(patients) == 6

        visits = db.scalars(select(Visit)).all()
        assert len(visits) >= 6

    # 2. Run seed a second time (idempotency check)
    stats2 = seed_demo()
    assert stats2["users_seeded"] == 3
    assert stats2["patients_seeded"] == 0
    assert stats2["visits_seeded"] == 0
