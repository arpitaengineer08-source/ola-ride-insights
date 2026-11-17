# Contributing

Thanks for your interest in improving Ola Ride Insights.

## Getting started
1. Fork and clone the repository.
2. Create a Python virtual environment.
3. Install dependencies using `pip install -r requirements.txt`.
4. Follow the README to build the local database and start the Streamlit app.

## Contribution guidelines
- Preserve documented booking-status and revenue definitions.
- Keep raw-source validation and data-quality checks intact.
- Add or update tests when changing ETL, SQL, analytics or application behaviour.
- Run `pytest` before opening a pull request.
- Do not commit credentials, local databases or unrelated generated files.

## Pull requests
Explain the business question addressed, implementation details, tests run and any impact on dashboard metrics. Include screenshots for UI changes where useful.
