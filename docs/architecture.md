# Architecture Overview

This project follows a layered Flask architecture:

## Layers

### Routes
- Handle HTTP requests
- No business logic
- Call services

### Services
- Business rules
- Database transactions
- Reusable logic

### Models
- Database schema
- Relationships only

## Why This Matters

- Easier testing
- Safer refactoring
- Clear ownership of logic