from ..extensions import db


class Job(db.Model):
    __tablename__ = "jobs"

    id = db.Column(db.Integer, primary_key=True)
    vehicle_id = db.Column(db.Integer, db.ForeignKey("vehicles.id"), nullable=False)

    description = db.Column(db.Text, nullable=False)
    status = db.Column(db.String(50), default="open")
    cost = db.Column(db.Float)

    vehicle = db.relationship("Vehicle", back_populates="jobs")

    def __repr__(self):
        return f"<Job {self.id} status={self.status}>"
