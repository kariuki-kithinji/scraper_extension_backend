import hashlib
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.dialects.postgresql import JSON
from datetime import datetime

db = SQLAlchemy()

class TimestampMixin:
    """Mixin to add created and updated timestamps."""
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

class SiteRecord(db.Model, TimestampMixin):
    __tablename__ = 'site_records'

    id = db.Column(db.Integer, primary_key=True)
    url = db.Column(db.String(255), unique=True, nullable=False, index=True)
    data = db.Column(JSON, nullable=False, default={})
    flagged = db.Column(db.Boolean, default=False, index=True)
    saved = db.Column(db.Boolean, default=False, index=True)
    html_hash = db.Column(db.String(32), nullable=True)

    # Foreign keys to task records
    social_task_id = db.Column(db.Integer, db.ForeignKey('task_records.id'), nullable=True)
    classifier_task_id = db.Column(db.Integer, db.ForeignKey('task_records.id'), nullable=True)
    location_task_id = db.Column(db.Integer, db.ForeignKey('task_records.id'), nullable=True)

    # Relationships to TaskRecord
    social_task = db.relationship('TaskRecord', foreign_keys=[social_task_id])
    classifier_task = db.relationship('TaskRecord', foreign_keys=[classifier_task_id])
    location_task = db.relationship('TaskRecord', foreign_keys=[location_task_id])

    def __repr__(self):
        return f'<SiteRecord {self.url}>'

    def to_dict(self):
        return {
            'id': self.id,
            'url': self.url,
            'data': self.data,
            'flagged': self.flagged,
            'saved': self.saved,
            'html_hash': self.html_hash,
            'social_task': self.social_task.to_dict() if self.social_task else None,
            'classifier_task': self.classifier_task.to_dict() if self.classifier_task else None,
            'location_task': self.location_task.to_dict() if self.location_task else None,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat()
        }

    @staticmethod
    def calculate_html_hash(html):
        """Helper method to calculate MD5 hash of HTML content."""
        return hashlib.md5(html.encode('utf-8')).hexdigest()

class TaskRecord(db.Model, TimestampMixin):
    __tablename__ = 'task_records'

    id = db.Column(db.Integer, primary_key=True)
    task_id = db.Column(db.String(255), unique=True, nullable=False, index=True)
    state = db.Column(db.String(50), nullable=False)
    result = db.Column(JSON, nullable=True)

    def __repr__(self):
        return f'<TaskRecord {self.task_id}>'

    def to_dict(self):
        return {
            'task_id': self.task_id,
            'state': self.state,
            'result': self.result,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat()
        }
