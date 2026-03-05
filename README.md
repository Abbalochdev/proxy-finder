# Proxy Finder

[![Python](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)
[![GitHub issues](https://img.shields.io/github/issues/Abbalochdev/proxy-finder)](https://github.com/Abbalochdev/proxy-finder/issues)

A powerful command-line tool for managing and rotating IP proxies with real-time validation and country-specific filtering.
![Image](https://github.com/user-attachments/assets/1f59137a-9b73-488f-89a7-291280166105)

## Features

- 🌍 Fetch proxies from multiple reliable sources
- ⚡ Real-time proxy validation
- 🌐 Country-specific proxy filtering
- 🔒 Anonymity level filtering
- 🔄 Automatic proxy rotation
- 📊 Detailed proxy information display
- 🔄 Multiple country support
- ⏱️ Customizable connection timeouts
- 🔄 Proxy pool management
- 🔄 Automatic proxy rotation
- 📊 Detailed proxy statistics

## Installation

### Prerequisites
- Python 3.8 or higher
- pip (Python package manager)

### Install from Source

```bash
# Clone the repository
git clone https://github.com/Abbalochdev/proxy-finder.git
cd proxy-finder

# Install dependencies
pip install -r requirements.txt

# Install the package
pip install .
```

## Usage

### Basic Commands

```bash
# Fetch proxies
proxy-finder fetch -n 5

# Fetch specific number of proxies
proxy-finder fetch -n 10

# Fetch proxies from specific country
proxy-finder fetch -c US -n 5

# Fetch proxies from multiple countries
proxy-finder fetch -c US,GB,DE -n 10

# Validate proxies
proxy-finder validate

# Rotate proxies
proxy-finder rotate

# List available countries
proxy-finder countries
```

### Advanced Usage

```bash
# Fetch with specific anonymity level
proxy-finder fetch -c US -a anonymous -n 5

# Set custom timeout
proxy-finder fetch -t 5.0 -n 5

# Sort by speed
proxy-finder fetch -s speed -n 5

# Sort by country
proxy-finder fetch -s country -n 5

# Sort by anonymity level
proxy-finder fetch -s anonymity -n 5

# Sort by computed quality score (best overall first)
proxy-finder fetch -s quality -n 5
```

## Command Reference

```bash
# Available commands
proxy-finder fetch     # Fetch proxies from sources
proxy-finder validate  # Validate proxy connections
proxy-finder rotate    # Rotate between proxies
proxy-finder countries # List available countries

# Common options
-n, --number    # Number of proxies to retrieve
-c, --country   # Two-letter country code (e.g., US, GB)
-a, --anonymity # Anonymity level (transparent, anonymous, elite)
-t, --timeout   # Connection timeout in seconds
-s, --sort      # Sort results by field (speed, country, anonymity, quality)
```

## Proxy Information

Each proxy displays the following information:

- IP Address and Port
- Country of origin
- Anonymity level
- Quality score (0-100)
- Response speed
- Authentication status
- Last checked timestamp

## Contributing

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Support

For support, please:

1. Check the [issues](https://github.com/Abbalochdev/proxy-finder/issues) page
2. Create a new issue if your problem isn't listed

## Acknowledgments

- Thanks to all contributors and users who have helped improve this project
- Special thanks to the maintainers of the proxy sources used in this project

## Project Structure

```
proxy-finder/
├── src/
│   └── proxy_finder/
│       ├── core/
│       │   ├── fetcher.py     # Proxy fetching logic
│       │   ├── validator.py   # Proxy validation
│       │   └── rotation.py    # Proxy rotation
│       ├── utils/
│       │   ├── config.py      # Configuration management
│       │   └── logging.py     # Custom logging
│       └── cli.py             # Command-line interface
├── tests/                     # Test files
├── requirements.txt           # Production dependencies
├── requirements-dev.txt       # Development dependencies
└── docs/                      # Documentation
```

## Best Practices

1. Always validate proxies before using them
2. Use appropriate timeouts based on your needs
3. Rotate proxies regularly to maintain reliability
4. Monitor proxy performance using the speed metric
5. Use country filtering for location-specific tasks
6. Choose appropriate anonymity levels for your use case

## Troubleshooting

- If no proxies are found, try:
  - Using different countries
  - Increasing the timeout
  - Checking your internet connection
  - Using different anonymity levels

- If proxies are slow:
  - Sort by speed
  - Use a shorter timeout
  - Try different proxy sources

## Security Notice

- Never use untrusted proxies for sensitive operations
- Always validate proxy connections
- Use appropriate authentication when required
- Monitor proxy performance regularly
- Rotate proxies frequently for security

## Performance Tips

1. Use appropriate timeouts (default: 10 seconds)
2. Sort proxies by speed for best performance
3. Use country filtering to reduce latency
4. Rotate proxies regularly to maintain reliability
5. Monitor proxy performance metrics

## Future Development

Planned features:

- More proxy sources
- Enhanced validation methods
- Better error handling
- Additional sorting options
- More detailed statistics
- Improved country filtering
- Better proxy rotation algorithms
- Additional proxy metrics
- More configuration options

## Contact

For questions, suggestions, or bug reports:

- Email: developerno424@gmail.com
- GitHub: https://github.com/Abbalochdev/proxy-finder

## Disclaimer

This tool is provided as-is, without warranty of any kind. Use at your own risk.
