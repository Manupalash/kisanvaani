# KisanVaani - Project Instructions

## Product
KisanVaani is a voice-first agricultural AI assistant
for Telugu-speaking Indian farmers.

Primary language:
- Telugu
- Telugu-English code-mixed speech

## Architecture
- frontend/: Next.js, TypeScript, Tailwind CSS
- backend/: Python, FastAPI, SQLAlchemy
- Database: SQLite initially
- AI: Gnani Prisma for speech-to-text; optional, configured reasoning provider for agricultural answers

## Frontend conventions
- Use functional React components.
- Use TypeScript strictly.
- Keep components reusable.
- Use responsive, mobile-first layouts.
- Use Noto Sans Telugu.
- Use Lucide icons.
- Keep API calls inside frontend/src/lib/api.ts.
- Never expose API keys in frontend code.

## Backend conventions
- Use FastAPI.
- Use SQLAlchemy 2.0 patterns.
- Use Pydantic schemas.
- Separate routes, models and services.
- Use dependency injection for database sessions.
- Keep AI integrations inside services/.
- Validate all incoming data.
- Handle errors explicitly.

## AI conventions
- Use actual Gnani APIs when implementing integrations.
- Never invent API endpoints or request formats.
- Read official API documentation.
- Never expose API credentials.
- Validate model-generated JSON.
- Preserve conversation context.
- Ground agricultural recommendations in verified sources.

## Development rules
- Do not rewrite unrelated files.
- Do not introduce unnecessary dependencies.
- Do not leave broken imports.
- Run tests after implementation.
- Report modified files and commands executed.
- Never claim an integration works without testing it.

## Design direction
- Forest green: #173E32
- Harvest gold: #E8B95F
- Warm background: #F7F5ED
- White cards
- Premium agricultural technology aesthetic
- Mobile-first interface
- Accessible controls for low digital literacy

## Scope
Implement one phase at a time.
Do not start the next phase without explicit approval.