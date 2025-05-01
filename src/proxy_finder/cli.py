import argparse
import sys
import time
import logging
from typing import List, Dict, Any
from rich.console import Console
from rich.table import Table
from rich.progress import Progress, SpinnerColumn, BarColumn, TextColumn, TimeRemainingColumn
from rich.panel import Panel
from rich.text import Text
from rich.layout import Layout
from rich.live import Live
from rich import box
from rich.console import Group
from rich.columns import Columns

from .core.rotation import ProxyManager
from .core.enhanced_fetcher import ProxyFetcher
from .core.validator import ProxyValidator
from .core.country_fetcher import CountryProxyFetcher
from .utils.config import ConfigManager
from .utils.logging import setup_logging
from .exceptions import ProxyFetchError

def display_proxy_table(proxies: List[Dict[str, Any]], console: Console):
    """
    Display proxies in a formatted table with modern styling
    """
    if not proxies:
        console.print(Panel("[red]No valid proxies found. Try again with different filters.[/red]", 
                           border_style="red", box=box.ROUNDED))
        return

    # Create a modern styled table
    table = Table(
        show_header=True, 
        header_style="bold cyan", 
        box=box.ROUNDED,
        border_style="blue",
        title="[bold blue]Proxy Results[/bold blue]",
        title_justify="center",
        highlight=True
    )
    
    table.add_column("IP", style="cyan", width=20, no_wrap=True)
    table.add_column("Port", style="green", width=8, justify="right")
    table.add_column("Country", style="yellow", width=10)
    table.add_column("Anonymity", style="magenta", width=12)
    table.add_column("Speed", style="red", width=10)
    table.add_column("Auth", style="blue", width=8)
    table.add_column("Status", style="bright_blue", width=10)
    table.add_column("Last Checked", style="green", width=20)
    
    valid_proxies = []
    
    # Create an advanced progress indicator
    progress_columns = [
        SpinnerColumn(),
        "[progress.description]{task.description}",
        BarColumn(bar_width=40, style="blue", complete_style="green"),
        "[progress.percentage]{task.percentage:>3.0f}%",
        "•",
        TimeRemainingColumn()
    ]
    
    # Add rows with enhanced loading indicator
    with Progress(*progress_columns, console=console) as progress:
        task = progress.add_task("[cyan]Processing proxies...", total=len(proxies))
        
        for proxy in proxies:
            progress.advance(task)
            
            try:
                # Format speed with color based on performance
                speed = float(proxy.get('speed', 0))
                speed_str = str(round(speed, 2))
                if speed < 1.0:
                    speed_str = f"[green]{speed_str}s[/green]"
                elif speed < 3.0:
                    speed_str = f"[yellow]{speed_str}s[/yellow]"
                else:
                    speed_str = f"[red]{speed_str}s[/red]"
                
                # Split proxy into IP and port for better display
                proxy_str = proxy.get('proxy', '')
                if not proxy_str or not isinstance(proxy_str, str):
                    continue
                    
                if ':' in proxy_str:
                    ip, port = proxy_str.split(':', 1)
                else:
                    ip = proxy_str
                    port = ""
                
                if not ip:
                    continue
                
                # Check validation status
                validated = proxy.get('validated', False)
                status = "[green]Validated[/green]" if validated else "[yellow]Unvalidated[/yellow]"
                
                table.add_row(
                    ip,
                    port,
                    proxy.get('country', ''),
                    proxy.get('anonymity', ''),
                    speed_str,
                    proxy.get('auth', ''),
                    status,
                    proxy.get('last_checked', '')
                )
                valid_proxies.append(proxy)
                
            except Exception as e:
                logging.warning(f"Error processing proxy {proxy}: {e}")
                continue
    
    if not valid_proxies:
        console.print(Panel("[red]No valid proxies found after processing.[/red]", 
                          border_style="red", box=box.ROUNDED))
        return
        
    console.print(table)
    
    # Add summary statistics in a more attractive panel
    total_proxies = len(valid_proxies)
    avg_speed = sum(p.get('speed', 0) for p in valid_proxies) / total_proxies if total_proxies > 0 else 0
    fastest = min(valid_proxies, key=lambda x: x.get('speed', float('inf'))) if valid_proxies else None
    slowest = max(valid_proxies, key=lambda x: x.get('speed', float('inf'))) if valid_proxies else None
    
    stats_content = Group(
        Text("Proxy Statistics", style="bold cyan underline"),
        Text(f"Total proxies found: {total_proxies}", style="green"),
        Text(f"Average speed: {round(avg_speed, 2)}s", style="yellow"),
        Text(f"Fastest proxy: {fastest['proxy']} ({round(fastest.get('speed', 0), 2)}s)", style="green") if fastest else Text(""),
        Text(f"Slowest proxy: {slowest['proxy']} ({round(slowest.get('speed', 0), 2)}s)", style="red") if slowest else Text("")
    )
    
    console.print(Panel(stats_content, box=box.ROUNDED, border_style="blue"))
        
    # Add warning for limited proxy countries in a styled panel
    limited_proxy_countries = ['SA', 'IR', 'KP', 'CU', 'SY', 'VE']
    is_limited_country = False
    
    for proxy in valid_proxies:
        country = proxy.get('country', '').upper()
        if country in limited_proxy_countries:
            is_limited_country = True
            break
            
    if is_limited_country:
        warning_content = Group(
            Text("⚠️ Note", style="bold yellow"),
            Text("Some proxies are from countries with limited availability (SA, IR, etc.).", style="yellow"),
            Text("These proxies may be less reliable and might require validation before use.", style="yellow")
        )
        console.print(Panel(warning_content, box=box.ROUNDED, border_style="yellow"))

def create_app_header(console: Console):
    """Create an attractive header for the application"""
    title_text = Text()
    title_text.append("📡 ", style="bold yellow")
    title_text.append("PROXY", style="bold cyan")
    title_text.append(" FINDER", style="bold green")
    
    subtitle = Text("A powerful proxy management tool with advanced features", style="italic")
    
    features = [
        "[bold cyan]✓[/bold cyan] [white]Find proxies from multiple sources[/white]",
        "[bold cyan]✓[/bold cyan] [white]Validate connections automatically[/white]",
        "[bold cyan]✓[/bold cyan] [white]Rotate proxies during usage[/white]",
        "[bold cyan]✓[/bold cyan] [white]Filter by country and anonymity[/white]",
        "[bold cyan]✓[/bold cyan] [white]Smart proxy selection algorithms[/white]"
    ]
    
    features_group = Group(
        *[Text.from_markup(feature) for feature in features]
    )
    
    content = Group(
        title_text,
        Text(""),
        subtitle,
        Text(""),
        features_group
    )
    
    return Panel(
        content,
        box=box.ROUNDED,
        border_style="blue",
        padding=(1, 2),
        highlight=True
    )

def main():
    """
    Command-line interface for proxy finder.
    """
    console = Console()
    logger = setup_logging()
    
    # Display attractive header
    console.print(create_app_header(console))
    
    parser = argparse.ArgumentParser(description='Proxy Finder CLI')
    parser.add_argument('action', choices=['fetch', 'validate', 'rotate', 'countries'], 
                        help='Action to perform')
    parser.add_argument('-n', '--number', type=int, default=5, 
                        help='Number of proxies to retrieve')
    parser.add_argument('-c', '--country', type=str, 
                        help='Two-letter country code to filter proxies (e.g., US, GB) or comma-separated list (e.g., US,GB,DE)')
    parser.add_argument('-a', '--anonymity', type=str, choices=['transparent', 'anonymous', 'elite'],
                        help='Filter by anonymity level')
    parser.add_argument('-t', '--timeout', type=float, default=10.0,
                        help='Connection timeout in seconds')
    parser.add_argument('-s', '--sort', type=str, choices=['speed', 'country', 'anonymity'],
                        default='speed', help='Sort results by this field')
    
    args = parser.parse_args()
    
    try:
        # Create components with user-specified parameters
        config_manager = ConfigManager()
        
        if args.action == 'countries':
            # Get all available countries from the enhanced fetcher
            try:
                with Progress(
                    SpinnerColumn(),
                    TextColumn("[progress.description]{task.description}"),
                    BarColumn(bar_width=50),
                    TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
                    TimeRemainingColumn(),
                    console=console
                ) as progress:
                    task = progress.add_task("[cyan]Loading country data...", total=100)
                    
                    # Simulate progress while loading countries
                    for p in range(100):
                        if p == 20:
                            fetcher = ProxyFetcher(timeout=args.timeout)
                            all_countries = fetcher.get_available_countries()
                        progress.update(task, completed=p + 1)
                        time.sleep(0.01)
                
                # Group countries by continent for better organization
                continents = {
                    'North America': ['US', 'CA', 'MX'],
                    'South America': ['BR', 'AR', 'CL', 'CO', 'PE', 'VE'],
                    'Europe': ['GB', 'DE', 'FR', 'IT', 'ES', 'NL', 'BE', 'CH', 'AT', 'SE', 'NO', 'DK', 'FI', 'PT', 'GR', 'IE', 'PL', 'CZ', 'HU', 'RO', 'BG', 'HR', 'RS', 'SK', 'SI', 'LT', 'LV', 'EE'],
                    'Asia': ['RU', 'CN', 'JP', 'KR', 'IN', 'SG', 'TH', 'MY', 'ID', 'PH', 'VN', 'HK', 'TW', 'IL', 'TR', 'AE', 'SA', 'QA', 'PK', 'BD'],
                    'Oceania': ['AU', 'NZ'],
                    'Africa': ['ZA', 'EG', 'MA', 'NG', 'KE', 'DZ', 'TN']
                }
                
                # Create panels for continents
                continent_panels = []
                
                # Create a panel for each continent
                for continent, codes in continents.items():
                    # Filter countries that exist in our available countries
                    continent_countries = {code: all_countries.get(code, code) for code in codes if code in all_countries}
                    
                    if continent_countries:
                        # Create table for this continent
                        table = Table(show_header=True, header_style="bold green", box=box.ROUNDED)
                        table.add_column("Code", style="cyan", width=6)
                        table.add_column("Country", style="white")
                        
                        for code, name in sorted(continent_countries.items()):
                            table.add_row(code, name)
                        
                        # Add panel with table
                        panel = Panel(
                            table, 
                            title=f"[bold blue]{continent}[/bold blue]", 
                            border_style="blue",
                            box=box.ROUNDED
                        )
                        continent_panels.append(panel)
                
                # Display continents in columns
                console.print(Columns(continent_panels))
                
                # Add other countries that weren't in the continent groups
                other_countries = {code: name for code, name in all_countries.items() 
                                 if not any(code in codes for codes in continents.values())}
                
                if other_countries:
                    table = Table(show_header=True, header_style="bold magenta", box=box.ROUNDED)
                    table.add_column("Code", style="cyan", width=6)
                    table.add_column("Country", style="white")
                    
                    for code, name in sorted(other_countries.items()):
                        table.add_row(code, name)
                    
                    panel = Panel(table, title="[bold blue]Other Countries[/bold blue]", border_style="blue", box=box.ROUNDED)
                    console.print(panel)
                
                # Add usage instructions
                usage_text = Group(
                    Text("How to Use Country Codes", style="bold yellow underline"),
                    Text(""),
                    Text.from_markup("Basic usage: [bold green]proxy-finder fetch -c US -n 5[/bold green]"),
                    Text("This will fetch 5 proxies from the United States."),
                    Text(""),
                    Text.from_markup("For multiple countries: [bold green]proxy-finder fetch -c US,GB,DE -n 10[/bold green]"),
                    Text("This will fetch 10 proxies from the US, UK, and Germany.")
                )
                
                console.print(Panel(usage_text, border_style="yellow", box=box.ROUNDED))
            except Exception as e:
                logger.error(f"Error displaying countries: {e}")
                console.print(Panel("[red]Error retrieving country list. Here are the most common country codes:[/red]", 
                                   border_style="red", box=box.ROUNDED))
                
                # Show a hardcoded list of common countries as fallback
                common_countries = {
                    "US": "United States",
                    "GB": "United Kingdom",
                    "DE": "Germany",
                    "FR": "France",
                    "IT": "Italy",
                    "ES": "Spain",
                    "CA": "Canada",
                    "AU": "Australia",
                    "RU": "Russia",
                    "JP": "Japan",
                    "IN": "India",
                    "BR": "Brazil",
                    "CN": "China"
                }
                
                table = Table(show_header=True, header_style="bold magenta", box=box.ROUNDED)
                table.add_column("Code", style="cyan", width=6)
                table.add_column("Country", style="white")
                
                for code, name in sorted(common_countries.items()):
                    table.add_row(code, name)
                
                console.print(Panel(table, border_style="blue", box=box.ROUNDED))
            return
        
        # For other actions, create a proxy manager with country filter if specified
        # Handle multiple countries if provided with comma separation
        countries = None
        if args.country:
            if ',' in args.country:
                countries = [c.strip().upper() for c in args.country.split(',')]
                # Display the countries being searched
                country_list = ", ".join(countries)
                console.print(Panel(f"[cyan]Looking for proxies from countries: {country_list}[/cyan]", 
                                   border_style="blue", box=box.ROUNDED))
            else:
                countries = [args.country.strip().upper()]
                console.print(Panel(f"[cyan]Looking for proxies from country: {countries[0]}[/cyan]", 
                                   border_style="blue", box=box.ROUNDED))
        
        # Store proxies found for all execution modes
        all_proxies = []
            
        if countries:
            # Use country-specific fetcher for better results
            try:
                for country in countries:
                    console.print(f"[bold cyan]► Fetching proxies from country: {country}[/bold cyan]")
                    try:
                        proxy_fetcher = CountryProxyFetcher(country_code=country, timeout=args.timeout)
                        try:
                            # Create a nice progress spinner for fetching
                            with Progress(
                                SpinnerColumn(), 
                                TextColumn("[progress.description]{task.description}"),
                                BarColumn(complete_style="green"), 
                                console=console
                            ) as progress:
                                fetch_task = progress.add_task(f"[cyan]Fetching proxies from {country}...", total=None)
                                country_proxies = proxy_fetcher.fetch_proxies(max_proxies=args.number)
                                progress.update(fetch_task, completed=True, description=f"[green]Found {len(country_proxies)} proxies for {country}")
                                
                            all_proxies.extend(country_proxies)
                            logger.info(f"Found {len(country_proxies)} proxies for {country} from country-specific fetcher")
                        except ProxyFetchError as e:
                            console.print(f"[yellow]⚠️ Warning: {e}[/yellow]")
                            logger.warning(f"ProxyFetchError for {country}: {e}")
                    except Exception as e:
                        console.print(f"[yellow]⚠️ Error fetching from {country}: {e}[/yellow]")
                        logger.warning(f"Error fetching from {country}: {e}")
                        continue
                            
                # If we don't have enough proxies, fall back to the enhanced fetcher
                if len(all_proxies) < args.number:
                    console.print(Panel("[cyan]Trying enhanced fetcher as fallback...[/cyan]", 
                                       border_style="blue", box=box.ROUNDED))
                    # Try each country with the enhanced fetcher
                    for country in countries:
                        console.print(f"[bold cyan]► Fetching from enhanced sources for country: {country}[/bold cyan]")
                        try:
                            enhanced_fetcher = ProxyFetcher(country=country, timeout=args.timeout)
                            try:
                                # Create a nice progress spinner for fetching
                                with Progress(
                                    SpinnerColumn(), 
                                    TextColumn("[progress.description]{task.description}"),
                                    BarColumn(complete_style="green"), 
                                    console=console
                                ) as progress:
                                    fetch_task = progress.add_task(f"[cyan]Searching enhanced sources...", total=None)
                                    enhanced_proxies = enhanced_fetcher.fetch_proxies(max_proxies=args.number)
                                    progress.update(fetch_task, completed=True, description=f"[green]Found {len(enhanced_proxies)} proxies from enhanced sources")
                                    
                                all_proxies.extend(enhanced_proxies)
                                logger.info(f"Found {len(enhanced_proxies)} proxies for {country} from enhanced fetcher")
                            except ProxyFetchError as e:
                                logger.warning(f"Enhanced fetcher error for {country}: {e}")
                                pass
                        except Exception as e:
                            console.print(f"[yellow]⚠️ Error with enhanced fetcher for {country}: {e}[/yellow]")
                            logger.warning(f"Error with enhanced fetcher for {country}: {e}")
                            continue
                             
                # Last resort: try to use any proxy with the requested country tag even if validation failed
                if len(all_proxies) == 0 and countries:
                    console.print(Panel("[yellow]No validated proxies found. Trying to fetch raw proxies for your country...[/yellow]",
                                      border_style="yellow", box=box.ROUNDED))
                    try:
                        # Simple fallback fetcher with progress indicator
                        with Progress(
                            SpinnerColumn(), 
                            TextColumn("[progress.description]{task.description}"),
                            BarColumn(complete_style="yellow"), 
                            console=console
                        ) as progress:
                            task = progress.add_task("[yellow]Last resort search...", total=None)
                            generic_fetcher = ProxyFetcher(timeout=max(15.0, args.timeout))
                            raw_proxies = generic_fetcher.fetch_proxies(max_proxies=100)
                            
                            # Manual filtering for country
                            filtered_count = 0
                            for country in countries:
                                for proxy in raw_proxies:
                                    if proxy.get('country', '').upper() == country.upper():
                                        all_proxies.append(proxy)
                                        filtered_count += 1
                                        
                            progress.update(task, completed=True, description=f"[green]Found {filtered_count} raw proxies")
                                
                        logger.info(f"Found {len(all_proxies)} raw proxies after last-resort filtering")
                    except Exception as e:
                        logger.warning(f"Last resort fetching failed: {e}")
                        
            except ValueError as e:
                console.print(Panel(f"[red]Error: {e}[/red]", border_style="red", box=box.ROUNDED))
                console.print("[yellow]Valid country codes include:[/yellow]")
                console.print("[cyan]US (United States), GB (United Kingdom), DE (Germany), FR (France),[/cyan]")
                console.print("[cyan]JP (Japan), CA (Canada), AU (Australia), IN (India), etc.[/cyan]")
                console.print("[cyan]Use 'countries' command to see all available country codes.[/cyan]")
                sys.exit(1)
        else:
            # Use the regular fetcher for all countries
            try:
                with Progress(
                    SpinnerColumn(), 
                    TextColumn("[progress.description]{task.description}"),
                    BarColumn(complete_style="green"), 
                    console=console
                ) as progress:
                    task = progress.add_task("[cyan]Fetching proxies from global sources...", total=None)
                    proxy_manager = ProxyManager(timeout=args.timeout)
                    all_proxies = proxy_manager.fetcher.fetch_proxies()
                    progress.update(task, completed=True, description=f"[green]Found {len(all_proxies)} proxies")
            except Exception as e:
                console.print(Panel(f"[red]Error fetching proxies: {e}[/red]", border_style="red", box=box.ROUNDED))
                logger.error(f"Error fetching proxies: {e}")
                sys.exit(1)
            
        # De-duplicate proxies
        unique_proxies = []
        seen_proxies = set()
        for proxy in all_proxies:
            proxy_str = proxy.get('proxy')
            if proxy_str and proxy_str not in seen_proxies:
                seen_proxies.add(proxy_str)
                unique_proxies.append(proxy)
                
        all_proxies = unique_proxies
        
        # Log the total number of unique proxies found before filtering
        logger.info(f"Found {len(all_proxies)} unique proxies before final filtering")
        console.print(Panel(f"[cyan]Found {len(all_proxies)} unique proxies total.[/cyan]", 
                          border_style="blue", box=box.ROUNDED))
        
        # If we have more proxies than requested, limit the number
        if len(all_proxies) > args.number:
            all_proxies = all_proxies[:args.number]
            console.print(f"[cyan]Limiting to {args.number} proxies as requested.[/cyan]")
        elif len(all_proxies) == 0:
            # No proxies found even after all sources
            console.print(Panel("[red]No proxies found. Try increasing the timeout or using different country codes.[/red]", 
                              border_style="red", box=box.ROUNDED))
            console.print("[yellow]For some countries like SA (Saudi Arabia), IR (Iran), or other restricted regions, proxies may be limited.[/yellow]")
            console.print("[yellow]Try popular country codes like US, GB, DE, FR, NL, CA for better results.[/yellow]")
            sys.exit(1)
        elif len(all_proxies) < args.number:
            # Found some but fewer than requested
            console.print(Panel(f"[yellow]Only found {len(all_proxies)} proxies. Requested {args.number}.[/yellow]", 
                              border_style="yellow", box=box.ROUNDED))
            console.print("[yellow]Try increasing timeout, using different country codes, or reducing the requested number.[/yellow]")
            
        if args.action == 'fetch':
            # Sort proxies based on the specified field
            if args.sort == 'speed':
                all_proxies = sorted(all_proxies, key=lambda x: x.get('speed', float('inf')))
            elif args.sort == 'country':
                all_proxies = sorted(all_proxies, key=lambda x: x.get('country', ''))
            elif args.sort == 'anonymity':
                all_proxies = sorted(all_proxies, key=lambda x: x.get('anonymity', ''))
            
            # Display the proxies in a formatted table
            display_proxy_table(all_proxies[:args.number], console)
        
        elif args.action == 'validate':
            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                BarColumn(bar_width=40, complete_style="green"),
                TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
                TimeRemainingColumn(),
                console=console
            ) as progress:
                task = progress.add_task("[cyan]Validating proxy...", total=100)
                
                for i in range(100):
                    time.sleep(0.01)
                    progress.update(task, completed=i + 1)
                    
                    if i == 50:
                        proxy_details = proxy_manager.get_proxy()
            
            if proxy_details:
                display_proxy_table([proxy_details], console)
            else:
                console.print(Panel("[red]No valid proxy found[/red]", border_style="red", box=box.ROUNDED))
        
        elif args.action == 'rotate':
            # For rotate action, limit the number of proxies for faster results
            num_proxies = min(5, args.number)
            
            # Initialize proxies list outside the try block to fix scope issues
            proxies = []
            
            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                BarColumn(bar_width=40, complete_style="green"),
                TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
                TimeRemainingColumn(),
                console=console
            ) as progress:
                task = progress.add_task(f"[cyan]Finding {num_proxies} proxies...", total=100)
                
                try:
                    # Use a more reasonable timeout for better success rate
                    proxy_manager.validator.timeout = min(8.0, args.timeout)
                    
                    # Get proxies with a timeout to prevent hanging
                    max_wait_time = 15  # Maximum seconds to wait
                    start_time = time.time()
                    
                    while len(proxies) < num_proxies and (time.time() - start_time) < max_wait_time:
                        try:
                            # Try to get one proxy at a time for better responsiveness
                            proxy = proxy_manager.get_proxy()
                            if proxy:
                                proxies.append(proxy)
                                # Update progress
                                progress.update(task, completed=(len(proxies) * 100 / num_proxies))
                        except Exception as e:
                            # If we hit an error, just continue
                            pass
                    
                    progress.update(task, completed=100)
                except Exception as e:
                    # If we hit an error, just show what we have
                    logger.warning(f"Error in rotate action: {e}")
                    progress.update(task, completed=100)
            
            # Filter by anonymity if specified and we have proxies
            if args.anonymity and proxies:
                proxies = [p for p in proxies if p.get('anonymity') == args.anonymity]
            
            # Sort results if we have proxies
            if proxies:
                if args.sort == 'speed':
                    proxies.sort(key=lambda x: x.get('speed', float('inf')))
                elif args.sort == 'country':
                    proxies.sort(key=lambda x: x.get('country', 'unknown'))
                elif args.sort == 'anonymity':
                    anonymity_rank = {'elite': 0, 'anonymous': 1, 'transparent': 2, 'unknown': 3}
                    proxies.sort(key=lambda x: anonymity_rank.get(x.get('anonymity', 'unknown'), 3))
            
            # Display results
            if proxies:
                display_proxy_table(proxies, console)
            else:
                console.print(Panel("[red]No valid proxies found. Try again or use different filters.[/red]", 
                                  border_style="red", box=box.ROUNDED))
    
    except Exception as e:
        logger.error(f"Error: {e}")
        console.print(Panel(f"[red]Error: {e}[/red]", border_style="red", box=box.ROUNDED))
        sys.exit(1)

if __name__ == '__main__':
    main()
