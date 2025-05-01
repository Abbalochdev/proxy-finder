# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.2.0] - 2025-05-01

### Added
- Enhanced modern UI with emojis and improved visual styling
- New status column in proxy table to show validation status
- Animated spinners and progress bars for all operations
- Special handling for countries with limited proxy availability
- Last-resort fallback mechanism for difficult-to-find country proxies
- Detailed statistics panel with improved formatting

### Changed
- Completely redesigned CLI interface with modern Rich components
- Improved country-specific proxy fetching with better source management
- Better error handling and user feedback for network issues
- Enhanced progress tracking with time estimates
- More attractive table and panel designs with rounded borders
- Redesigned header with feature highlights

### Fixed
- Fixed issue with proxies being lost during validation
- Fixed bug in rotate command's variable scope
- Improved handling of Saudi Arabia and other limited-proxy countries
- Better error messages for network timeouts

## [1.1.0] - 2025-04-30

### Added
- Progress indicator during proxy validation
- Loading indicator for better user feedback

### Changed
- Increased proxy validation timeout from 10.0 to 15.0 seconds
- Increased maximum validation timeout from 15.0 to 20.0 seconds
- Improved error handling in proxy validation
- Enhanced console output formatting

### Fixed
- Proxy validation timeout issues
- Progress tracking during proxy processing

## [1.0.0] - 2025-04-30

### Added
- Initial release of Proxy Finder
- Core proxy fetching functionality
- Basic proxy validation
- Command-line interface with rich text support
- Configuration management
- Logging system

[Unreleased]: https://github.com/Abbalochdev/proxy-finder/compare/v1.2.0...HEAD
[1.2.0]: https://github.com/Abbalochdev/proxy-finder/compare/v1.1.0...v1.2.0
[1.1.0]: https://github.com/Abbalochdev/proxy-finder/compare/v1.0.0...v1.1.0
[1.0.0]: https://github.com/Abbalochdev/proxy-finder/releases/tag/v1.0.0
