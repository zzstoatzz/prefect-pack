## Celery-ish work with `prefect` and `fastapi`

This is a simple docker compose app that runs an API that offloads work to a Prefect task worker.

>[!NOTE]
> This is very similar to how you'd use Celery in a common real-world application.

### Setup

Populate the `.env` file here in the `do_celery_stuff` directory with the following:

```bash
PREFECT_API_URL=http://localhost:4200/api # or prefect cloud url
PREFECT_API_KEY=pnu_1234567890abcdefghijklmnopqrstuvwxyz # if using prefect cloud
```

### Start the app
```bash
docker compose up -d
```

### Stream the logs
```bash
docker compose logs -f
```

### Stop the app
```bash
docker compose down
```
