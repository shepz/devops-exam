# Devops challenge

**TL; DR**: You're being given a python asgi web app, deploy it.

# The app

* It uses [poetry](https://poetry.eustace.io/) as packaging and dependency management tool;

* App expects 1 environment variable:
    * `DATABASE_URI`: Database's URI (postgres)
* Db migration uses `alembic` and expects 1 environment variable:
    * `ALEMBIC_DATABASE_URI`: Database's URI (postgres)
* Run DB migration: `alembic upgrade head`
* Run app: `hypercorn app:app`
* Documentation is on `/docs`

* Tests expects one environment variable
    * `TEST_DATABASE_URI`: Database's URI (postgres)
* Run tests: `pytest`

# The challenge

* Code everything needed to deploy this app on [minikube](https://github.com/kubernetes/minikube);
* Explain in few words what you would do to deploy this on production;
