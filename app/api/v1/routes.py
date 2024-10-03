from flask import jsonify, request, current_app
from app.api.v1 import bp
from app.models import SiteRecord, TaskRecord, db
from app.tasks import social_queue_manager, classifier_queue_manager, location_queue_manager, celery
from app.utils import cache, limiter
from celery.signals import task_success
from datetime import datetime
from sqlalchemy.exc import SQLAlchemyError
import requests as req


# Helper function to calculate hash and check existing record
def get_existing_site_record(url, html=None):
    """Check if the site record exists and handle HTML comparison if provided."""
    existing_record = SiteRecord.query.filter_by(url=url).first()
    new_html_hash = None

    if html:
        new_html_hash = SiteRecord.calculate_html_hash(html)

    if existing_record:
        if html and existing_record.html_hash == new_html_hash:
            # Same URL and HTML content, no need to reprocess
            return {
                'status': 'success',
                'message': 'No changes in HTML, returning task IDs',
                'record_id': existing_record.id,
                'tasks': {
                    'social': existing_record.social_task_id,
                    'classifier': existing_record.classifier_task_id,
                    'location': existing_record.location_task_id
                }
            }, existing_record, 200
        return None, existing_record, new_html_hash

    return None, None, new_html_hash

# Helper function to update or create a site record with the relevant task id
def update_or_create_site_record(url, new_html_hash=None, social_task_id=None, classifier_task_id=None, location_task_id=None):
    """Update the site record with the new task id or create a new record."""
    site_record = SiteRecord.query.filter_by(url=url).first()

    if site_record:
        if social_task_id:
            site_record.social_task_id = social_task_id
        if classifier_task_id:
            site_record.classifier_task_id = classifier_task_id
        if location_task_id:
            site_record.location_task_id = location_task_id
        if new_html_hash:
            site_record.html_hash = new_html_hash
    else:
        site_record = SiteRecord(
            url=url,
            html_hash=new_html_hash,
            social_task_id=social_task_id,
            classifier_task_id=classifier_task_id,
            location_task_id=location_task_id
        )
        db.session.add(site_record)

    db.session.commit()
    return site_record

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
        existing_response, existing_record, new_html_hash = get_existing_site_record(url, html)
      
        # Create new social analysis task
        social_task = social_queue_manager.apply_async(args=[html, url])

        # Update or create record in the database
        record = update_or_create_site_record(
            url=url,
            new_html_hash=new_html_hash,
            social_task_id=social_task.id
        )

        return jsonify({
            'status': 'success',
            'message': 'Social analysis task started',
            'task_id': social_task.id,
            'record_id':record.id
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
        url = request_data.get('url', '')

        if not html or not url:
            return jsonify({'status': 'error', 'message': 'HTML and URL are required'}), 400

        # Check if site already exists (no need for HTML comparison here)
        _, existing_record, new_html_hash = get_existing_site_record(url, html)

        # Create new classification analysis task
        classifier_task = classifier_queue_manager.apply_async(args=[html])

        # Update or create record in the database
        record = update_or_create_site_record(
            url=request_data.get('url', ''),
            new_html_hash=new_html_hash,
            classifier_task_id=classifier_task.id
        )

        return jsonify({
            'status': 'success',
            'message': 'Classification analysis task started',
            'task_id': classifier_task.id,
            'record_id': record.id
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

        # Check if site already exists (no need for HTML comparison here)
        _, existing_record, _ = get_existing_site_record(url)

        # Create new location analysis task
        location_task = location_queue_manager.apply_async(args=[url])

        # Update or create record in the database
        record = update_or_create_site_record(
            url=url,
            location_task_id=location_task.id
        )

        return jsonify({
            'status': 'success',
            'message': 'Location analysis task started',
            'task_id': location_task.id,
            'record_id':record.id
        }), 202

    except Exception as e:
        current_app.logger.error(f"Error in analyze_location: {str(e)}")
        return jsonify({'status': 'error', 'message': 'Internal server error'}), 500

# Task status checking endpoint
@bp.route('/tasks/<task_id>', methods=['GET'])
@limiter.limit("200/minute")
def get_task_status(task_id):
    task = celery.AsyncResult(task_id)
    
    # Save the task record if the task is done
    saved = save_task_record_if_done(task_id)

    return jsonify({
        'task_id': task.id,
        'state': task.state,
        'result': task.result if task.state == 'SUCCESS' else None,
    }), 200

@bp.route('/tasks/<task_id>/update', methods=['POST'])
@limiter.limit("200/minute")
def update_task_result(task_id):
    # Parse the new result from the JSON request body
    data = request.get_json()

    if not data or 'result' not in data:
        return jsonify({'error': 'Invalid request, "result" field is required.'}), 400

    # Find the task record in the database
    task_record = TaskRecord.query.filter_by(task_id=task_id).first()

    if not task_record:
        return jsonify({'error': 'Task record not found.'}), 404

    # Replace the existing result with the new one
    task_record.result = data['result']
    db.session.commit()

    return jsonify({
        'status': 'success',
        'message': 'Task result updated successfully.',
        'task_id': task_record.task_id,
        'new_result': task_record.result
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
        # Fetch all site records
        site_records = SiteRecord.query.all()

        # Prepare the response data
        response_data = []
        for record in site_records:
            record_dict = record.to_dict()

            # Function to serialize datetime objects
            def serialize_dates(data):
                if isinstance(data, dict):
                    return {key: serialize_dates(value) for key, value in data.items()}
                elif isinstance(data, list):
                    return [serialize_dates(item) for item in data]
                elif isinstance(data, datetime):
                    return data.isoformat()  # Convert datetime to ISO format
                return data

            # Function to fetch and save task details if not found
            def fetch_and_save_task(task_id):
                if task_id:
                    task = TaskRecord.query.filter_by(task_id=task_id).first()
                    if not task:
                        # Fetch task details from Celery
                        celery_task = celery.AsyncResult(task_id)
                        if celery_task.state == 'SUCCESS':
                            # Serialize the result to ensure it's JSON serializable
                            serialized_result = serialize_dates(celery_task.result)
                            # Create a new TaskRecord and save it
                            task = TaskRecord(
                                task_id=task_id,
                                state=celery_task.state,
                                result=serialized_result
                            )
                            db.session.add(task)
                            db.session.commit()
                            return {'task_id': task_id, 'state': celery_task.state, 'result': serialized_result}
                    else:
                        return task.to_dict()
                return None

            # Fetch tasks if not already in records
            record_dict['social_task'] = fetch_and_save_task(record.social_task_id)
            record_dict['classifier_task'] = fetch_and_save_task(record.classifier_task_id)
            record_dict['location_task'] = fetch_and_save_task(record.location_task_id)

            # Append the record dict to response data
            response_data.append(record_dict)

        # Return the data in a serialized format
        return jsonify(response_data), 200

    except SQLAlchemyError as e:
        # Log the specific error details for debugging
        current_app.logger.error(f"Database error in get_all_records: {str(e)}", exc_info=True)
        return jsonify({'status': 'error', 'message': 'Database error'}), 500

    except Exception as e:
        # Log the specific error details for debugging
        current_app.logger.error(f"Error in get_all_records: {str(e)}", exc_info=True)
        return jsonify({'status': 'error', 'message': 'Internal server error'}), 500

@bp.route('/records/<int:record_id>', methods=['DELETE'])
@limiter.limit("50/minute")
def delete_record(record_id):
    try:
        # Fetch the site record by ID or return a 404 if it doesn't exist
        site_record = SiteRecord.query.get_or_404(record_id)

        # Delete the record from the database
        db.session.delete(site_record)
        db.session.commit()

        # Invalidate the cache if caching is used
        cache.delete_memoized(get_cached_site_record, site_record.url)

        return jsonify({'status': 'success', 'message': 'Record deleted successfully'}), 200

    except SQLAlchemyError as e:
        db.session.rollback()  # Roll back the session in case of error
        current_app.logger.error(f"Database error while deleting record {record_id}: {str(e)}", exc_info=True)
        return jsonify({'status': 'error', 'message': 'Database error'}), 500

    except Exception as e:
        current_app.logger.error(f"Error while deleting record {record_id}: {str(e)}", exc_info=True)
        return jsonify({'status': 'error', 'message': 'Internal server error'}), 500


def save_task_record_if_done(task_id):
    task = celery.AsyncResult(task_id)
    print(task.result)

    if task.state == 'SUCCESS':
        # Check if a record with the same task_id already exists
        existing_record = db.session.query(TaskRecord).filter_by(task_id=task.id).first()

        if existing_record is None:
            # If no existing record, create a new one
            task_record = TaskRecord(
                task_id=task.id,
                state=task.state,
                result=task.result
            )
            db.session.add(task_record)
            db.session.commit()
            return True  # Indicates that the record was saved
        else:
            print(f"Record for task_id {task_id} already exists. No new record saved.")
    
    return False  # Indicates that the task was not done or the record already exists




@task_success.connect
def on_task_success(sender, result, **kwargs):
    task_id = sender.request.id
    #TODO: needs context to save : 

# Cached function to retrieve a site record
@cache.memoize(300)
def get_cached_site_record(url):
    return SiteRecord.query.filter_by(url=url).first()
