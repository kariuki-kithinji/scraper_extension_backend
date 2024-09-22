from flask import jsonify, request, current_app
from app.api.v1 import bp
from app.models import SiteRecord, TaskRecord, db
from app.tasks import social_queue_manager, classifier_queue_manager, location_queue_manager, celery
from app.utils import cache, limiter

from celery.signals import task_success, task_failure
from datetime import datetime
from sqlalchemy.orm import joinedload

# Helper function to calculate hash and check existing record
def get_existing_site_record(url, html):
    new_html_hash = SiteRecord.calculate_html_hash(html)
    existing_record = SiteRecord.query.filter_by(url=url).first()

    if existing_record and existing_record.html_hash == new_html_hash:
        return {
            'status': 'success',
            'message': 'No changes in HTML, returning task IDs',
            'record_id': existing_record.id,
            'tasks': {
                'social': existing_record.social_task_id,
                'classifier': existing_record.classifier_task_id,
                'location': existing_record.location_task_id
            }
        }, 200
    return None, new_html_hash

# Endpoint to handle social media analysis
@bp.route('/analysis/social', methods=['POST'])
@limiter.limit("100/minute")
def analyze_social():
    try:
        request_data = request.get_json()
        html = request_data.get('html', '')
        url = request_data.get('url', '')

        if not html or not url:
            return jsonify({'status': 'error', 'message': 'HTML and URL are required'}), 400

        # Check if site already exists with the same content
        existing_record, new_html_hash = get_existing_site_record(url, html)
        if existing_record:
            return jsonify(existing_record), 200

        # Create new social analysis task
        social_task = social_queue_manager.apply_async(args=[html, url])

        # Update or create record in the database
        site_record = SiteRecord.query.filter_by(url=url).first()
        if site_record:
            site_record.social_task_id = social_task.id
            site_record.html_hash = new_html_hash
        else:
            site_record = SiteRecord(url=url, html_hash=new_html_hash, social_task_id=social_task.id)
            db.session.add(site_record)
        db.session.commit()

        return jsonify({
            'status': 'success',
            'message': 'Social analysis task started',
            'task_id': social_task.id
        }), 202

    except Exception as e:
        current_app.logger.error(f"Error in analyze_social: {str(e)}")
        return jsonify({'status': 'error', 'message': 'Internal server error'}), 500

# Endpoint to handle classification analysis
@bp.route('/analysis/classification', methods=['POST'])
@limiter.limit("100/minute")
def analyze_classification():
    try:
        request_data = request.get_json()
        html = request_data.get('html', '')

        if not html:
            return jsonify({'status': 'error', 'message': 'HTML is required'}), 400

        # Create new classification analysis task
        classifier_task = classifier_queue_manager.apply_async(args=[html])

        return jsonify({
            'status': 'success',
            'message': 'Classification analysis task started',
            'task_id': classifier_task.id
        }), 202

    except Exception as e:
        current_app.logger.error(f"Error in analyze_classification: {str(e)}")
        return jsonify({'status': 'error', 'message': 'Internal server error'}), 500

# Endpoint to handle location analysis
@bp.route('/analysis/location', methods=['POST'])
@limiter.limit("100/minute")
def analyze_location():
    try:
        request_data = request.get_json()
        url = request_data.get('url', '')

        if not url:
            return jsonify({'status': 'error', 'message': 'URL is required'}), 400

        # Create new location analysis task
        location_task = location_queue_manager.apply_async(args=[url])

        return jsonify({
            'status': 'success',
            'message': 'Location analysis task started',
            'task_id': location_task.id
        }), 202

    except Exception as e:
        current_app.logger.error(f"Error in analyze_location: {str(e)}")
        return jsonify({'status': 'error', 'message': 'Internal server error'}), 500

# Task status checking endpoint
@bp.route('/tasks/<task_id>', methods=['GET'])
@limiter.limit("200/minute")
def get_task_status(task_id):
    task = celery.AsyncResult(task_id)
    return jsonify({
        'task_id': task.id,
        'state': task.state,
        'result': task.result if task.state == 'SUCCESS' else None
    }), 200

# Endpoint to flag a record
@bp.route('/records/<int:record_id>/flag', methods=['POST'])
@limiter.limit("100/minute")
def flag_record(record_id):
    try:
        site_record = SiteRecord.query.get_or_404(record_id)
        site_record.flagged = True
        db.session.commit()
        cache.delete_memoized(get_cached_site_record, site_record.url)
        return jsonify({'status': 'success', 'message': 'Record flagged successfully'}), 200
    except Exception as e:
        current_app.logger.error(f"Error in flag_record: {str(e)}")
        return jsonify({'status': 'error', 'message': 'Internal server error'}), 500

# Endpoint to save a record
@bp.route('/records/<int:record_id>/save', methods=['POST'])
@limiter.limit("100/minute")
def save_record(record_id):
    try:
        site_record = SiteRecord.query.get_or_404(record_id)
        site_record.saved = True
        db.session.commit()
        cache.delete_memoized(get_cached_site_record, site_record.url)
        return jsonify({'status': 'success', 'message': 'Record saved successfully'}), 200
    except Exception as e:
        current_app.logger.error(f"Error in save_record: {str(e)}")
        return jsonify({'status': 'error', 'message': 'Internal server error'}), 500

# Endpoint to get a specific record
@bp.route('/records/<int:record_id>', methods=['GET'])
@limiter.limit("200/minute")
def get_record(record_id):
    try:
        site_record = SiteRecord.query.get_or_404(record_id)
        return jsonify(site_record.to_dict()), 200
    except Exception as e:
        current_app.logger.error(f"Error in get_record: {str(e)}")
        return jsonify({'status': 'error', 'message': 'Internal server error'}), 500

@bp.route('/records', methods=['GET'])
@limiter.limit("100/minute")
def get_all_records():
    try:
        # Use joinedload to eagerly load related task records to avoid lazy loading issues
        site_records = SiteRecord.query.options(
            joinedload(SiteRecord.social_task),
            joinedload(SiteRecord.classifier_task),
            joinedload(SiteRecord.location_task)
        ).all()

        # Return the data in a serialized format
        return jsonify([record.to_dict() for record in site_records]), 200

    except Exception as e:
        # Log the specific error details for debugging
        current_app.logger.error(f"Error in get_all_records: {str(e)}", exc_info=True)
        return jsonify({'status': 'error', 'message': 'Internal server error'}), 500


# Signal handler to save a task's success in TaskRecord
@task_success.connect
def on_task_success(sender, result, **kwargs):
    try:
        task_id = sender.request.id
        # Check if a TaskRecord already exists for this task
        task_record = TaskRecord.query.filter_by(task_id=task_id).first()

        if task_record:
            task_record.state = 'SUCCESS'
            task_record.result = result
            task_record.updated_at = datetime.utcnow()
        else:
            # Create a new TaskRecord
            task_record = TaskRecord(
                task_id=task_id,
                state='SUCCESS',
                result=result
            )
            db.session.add(task_record)

        db.session.commit()
    except Exception as e:
        current_app.logger.error(f"Error saving task success: {e}")

# Signal handler to save a task's failure in TaskRecord
@task_failure.connect
def on_task_failure(sender, exception, traceback, **kwargs):
    try:
        task_id = sender.request.id
        # Check if a TaskRecord already exists for this task
        task_record = TaskRecord.query.filter_by(task_id=task_id).first()

        if task_record:
            task_record.state = 'FAILURE'
            task_record.result = {'error': str(exception), 'traceback': traceback}
            task_record.updated_at = datetime.utcnow()
        else:
            # Create a new TaskRecord
            task_record = TaskRecord(
                task_id=task_id,
                state='FAILURE',
                result={'error': str(exception), 'traceback': traceback}
            )
            db.session.add(task_record)

        db.session.commit()
    except Exception as e:
        current_app.logger.error(f"Error saving task failure: {e}")

# Cached function to retrieve a site record
@cache.memoize(300)
def get_cached_site_record(url):
    return SiteRecord.query.filter_by(url=url).first()
