# Dockerized Flask Application

This is a Dockerized version of our Flask application for site analysis.

## Prerequisites

- Docker
- Docker Compose

## Setup

1. Clone the repository
2. Create a `.env` file in the root directory and add your environment variables (use `sample.env` as a template)
3. Build and run the containers:

   ```
   docker compose up --build
   ```

4. The application will be available at `http://localhost:5000`

## Services

- `web`: The main Flask application
- `db`: PostgreSQL database
- `redis`: Redis for caching and Celery broker
- `celery_worker`: Celery worker for background tasks
- `celery_beat`: Celery beat for scheduled tasks

## API Endpoints

This outlines the endpoints available in our API. No authentication is required to access these endpoints.

## Table of Contents

1. [Analyze Social Media](#analyze-social-media)
2. [Analyze Classification](#analyze-classification)
3. [Analyze Location](#analyze-location)
4. [Get Task Status](#get-task-status)
5. [Flag Record](#flag-record)
6. [Save Record](#save-record)
7. [Get Specific Record](#get-specific-record)
8. [Get All Records](#get-all-records)

---

## Analyze Social Media

Initiates a social media analysis task for a given URL and HTML content.

- **URL:** `/api/v1/analysis/social`
- **Method:** `POST`
- **Rate Limit:** 100 requests per minute

### Request Body

```json
{
  "html": "string",
  "url": "string"
}
```

### Success Response

- **Code:** 202
- **Content:**

```json
{
  "status": "success",
  "message": "Social analysis task started",
  "task_id": "string"
}
```

### Error Response

- **Code:** 400
- **Content:**

```json
{
  "status": "error",
  "message": "HTML and URL are required"
}
```

- **Code:** 500
- **Content:**

```json
{
  "status": "error",
  "message": "Internal server error"
}
```

---

## Analyze Classification

Initiates a classification analysis task for given HTML content.

- **URL:** `/api/v1/analysis/classification`
- **Method:** `POST`
- **Rate Limit:** 100 requests per minute

### Request Body

```json
{
  "html": "string"
}
```

### Success Response

- **Code:** 202
- **Content:**

```json
{
  "status": "success",
  "message": "Classification analysis task started",
  "task_id": "string"
}
```

### Error Response

- **Code:** 400
- **Content:**

```json
{
  "status": "error",
  "message": "HTML is required"
}
```

- **Code:** 500
- **Content:**

```json
{
  "status": "error",
  "message": "Internal server error"
}
```

---

## Analyze Location

Initiates a location analysis task for a given URL.

- **URL:** `/api/v1/analysis/location`
- **Method:** `POST`
- **Rate Limit:** 100 requests per minute

### Request Body

```json
{
  "url": "string"
}
```

### Success Response

- **Code:** 202
- **Content:**

```json
{
  "status": "success",
  "message": "Location analysis task started",
  "task_id": "string"
}
```

### Error Response

- **Code:** 400
- **Content:**

```json
{
  "status": "error",
  "message": "URL is required"
}
```

- **Code:** 500
- **Content:**

```json
{
  "status": "error",
  "message": "Internal server error"
}
```

---

## Get Task Status

Retrieves the status of a specific task.

- **URL:** `/api/v1/tasks/<task_id>`
- **Method:** `GET`
- **Rate Limit:** 200 requests per minute

### URL Parameters

- `task_id`: The ID of the task to check

### Success Response

- **Code:** 200
- **Content:**

```json
{
  "task_id": "string",
  "state": "string",
  "result": "object|null"
}
```

---

## Flag Record

Flags a specific record.

- **URL:** `/api/v1/records/<record_id>/flag`
- **Method:** `POST`
- **Rate Limit:** 100 requests per minute

### URL Parameters

- `record_id`: The ID of the record to flag

### Success Response

- **Code:** 200
- **Content:**

```json
{
  "status": "success",
  "message": "Record flagged successfully"
}
```

### Error Response

- **Code:** 404
- **Content:** `Not Found`

- **Code:** 500
- **Content:**

```json
{
  "status": "error",
  "message": "Internal server error"
}
```

---

## Save Record

Marks a specific record as saved.

- **URL:** `/api/v1/records/<record_id>/save`
- **Method:** `POST`
- **Rate Limit:** 100 requests per minute

### URL Parameters

- `record_id`: The ID of the record to save

### Success Response

- **Code:** 200
- **Content:**

```json
{
  "status": "success",
  "message": "Record saved successfully"
}
```

### Error Response

- **Code:** 404
- **Content:** `Not Found`

- **Code:** 500
- **Content:**

```json
{
  "status": "error",
  "message": "Internal server error"
}
```

---

## Get Specific Record

Retrieves details of a specific record.

- **URL:** `/api/v1/records/<record_id>`
- **Method:** `GET`
- **Rate Limit:** 200 requests per minute

### URL Parameters

- `record_id`: The ID of the record to retrieve

### Success Response

- **Code:** 200
- **Content:** The record details (structure depends on the `to_dict()` method implementation)

### Error Response

- **Code:** 404
- **Content:** `Not Found`

- **Code:** 500
- **Content:**

```json
{
  "status": "error",
  "message": "Internal server error"
}
```

---

## Get All Records

Retrieves all records.

- **URL:** `/api/v1/records`
- **Method:** `GET`
- **Rate Limit:** 100 requests per minute

### Success Response

- **Code:** 200
- **Content:** An array of record objects (structure depends on the `to_dict()` method implementation)

### Error Response

- **Code:** 500
- **Content:**

```json
{
  "status": "error",
  "message": "Internal server error"
}
```

---

## Notes

- All endpoints are rate-limited. Exceeding the rate limit will result in a 429 Too Many Requests response.
- The API uses Celery for task management. Task IDs returned by analysis endpoints can be used with the Get Task Status endpoint to check the progress and results of long-running tasks.
- Records are cached for 300 seconds (5 minutes) to improve performance. Actions that modify records (such as flagging or saving) will invalidate the cache for that record.


## Development

To run the application in development mode:

```
docker compose up
```

This will start all services and enable hot-reloading for the Flask application.

## Production

For production deployment, ensure you set appropriate environment variables in the `.env` file and update the `docker-compose.yml` file as needed for your production environment.