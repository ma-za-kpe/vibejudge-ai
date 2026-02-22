# Contributing to VibeJudge AI

Thank you for your interest in contributing to VibeJudge AI! This project was built for the AWS 10,000 AIdeas competition.

## Development Setup

1. **Clone the repository**
```bash
git clone https://github.com/ma-za-kpe/vibejudge-ai.git
cd vibejudge-ai
```

2. **Create virtual environment**
```bash
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
```

3. **Install dependencies**
```bash
pip install -r requirements.txt
pip install -r requirements-dev.txt
```

4. **Set up environment variables**
```bash
cp .env.example .env
# Edit .env with your AWS credentials
```

5. **Run tests**
```bash
pytest tests/ -v
```

## Code Style

- Use Python 3.12+
- Follow PEP 8 style guide
- Add type hints to all functions
- Write docstrings for public functions
- Use absolute imports (not relative)
- Run `ruff check` before committing

## Testing

- Write unit tests for new features
- Ensure all tests pass before submitting PR
- Aim for high test coverage

## Pull Request Process

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## Questions?

Open an issue or reach out to maku@vibecoders.com

## License

By contributing, you agree that your contributions will be licensed under the MIT License.
