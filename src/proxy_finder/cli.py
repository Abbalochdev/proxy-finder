import argparse
import sys
import time
from typing import List, Dict, Any
from rich.console import Console
from rich.table import Table
from rich.progress import Progress
from rich.panel import Panel
from rich.text import Text

from .core.rotation import ProxyManager
from .core.enhanced_fetcher import ProxyFetcher
from .core.validator import ProxyValidator
from .core.country_fetcher import CountryProxyFetcher
from .utils.config import ConfigManager
from .utils.logging import setup_logging

def display_proxy_table(proxies: List[Dict[str, Any]], console: Console):
    """
    Display proxies in a formatted table
    """
    if not proxies:
        console.print("[red]No valid proxies found. Try again with different filters.[/red]")
        return

    # Create table with wider columns for better visibility
    table = Table(show_header=True, header_style="bold magenta", show_lines=True)
    table.add_column("IP", style="cyan", width=20, no_wrap=True)
    table.add_column("Port", style="cyan", width=8, justify="right")
    table.add_column("Country", style="green", width=10)
    table.add_column("Anonymity", style="yellow", width=12)
    table.add_column("Speed (s)", style="red", width=10)
    table.add_column("Auth", style="magenta", width=8)
    table.add_column("Last Checked", style="blue", width=20)
    
    # Add rows with loading indicator
    with Progress(console=console) as progress:
        task = progress.add_task("[cyan]Processing proxies...", total=len(proxies))
        for proxy in proxies:
            progress.advance(task)
            
            # Format speed with color based on performance
            speed = proxy.get('speed', 0)
            speed_str = str(round(speed, 2))
            if speed < 1.0:
                speed_str = f"[green]{speed_str}[/green]"
            elif speed < 3.0:
                speed_str = f"[yellow]{speed_str}[/yellow]"
            else:
                speed_str = f"[red]{speed_str}[/red]"
            
            # Split proxy into IP and port for better display
            proxy_str = proxy.get('proxy', 'unknown')
            if ':' in proxy_str:
                ip, port = proxy_str.split(':', 1)
            else:
                ip = proxy_str
                port = ""
            
            table.add_row(
                ip,
                port,
                proxy.get('country', ''),
                proxy.get('anonymity', ''),
                speed_str,
                proxy.get('auth', ''),
                proxy.get('last_checked', '')
            )
    
    console.print(table)
    
    # Add summary statistics
    total_proxies = len(proxies)
    avg_speed = sum(p.get('speed', 0) for p in proxies) / total_proxies if total_proxies > 0 else 0
    fastest = min(proxies, key=lambda x: x.get('speed', float('inf'))) if proxies else None
    slowest = max(proxies, key=lambda x: x.get('speed', float('inf'))) if proxies else None
    
    console.print("\n[bold]Proxy Statistics:[/bold]")
    console.print(f"Total proxies found: [cyan]{total_proxies}[/cyan]")
    console.print(f"Average speed: [cyan]{round(avg_speed, 2)}s[/cyan]")
    if fastest:
        console.print(f"Fastest proxy: [cyan]{fastest['proxy']} ({round(fastest['speed'], 2)}s)[/cyan]")
    if slowest:
        console.print(f"Slowest proxy: [cyan]{slowest['proxy']} ({round(slowest['speed'], 2)}s)[/cyan]")

def main():
    """
    Command-line interface for proxy finder.
    """
    console = Console()
    logger = setup_logging()
    
    # Add title and description
    title = "[bold blue]Proxy Finder[/bold blue]"
    description = """
    [bold]A powerful proxy management tool that helps you find, validate, and rotate proxies.
    Features:
    • Fetch proxies from multiple sources
    • Validate proxy connections
    • Rotate proxies automatically
    • Filter by country and anonymity level
    • Real-time progress tracking
    [/bold]
    """
    console.print(Panel(description, title=title, border_style="blue", padding=(1)))
    
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
            fetcher = ProxyFetcher()
            all_countries = fetcher.get_available_countries()
            
            # Group countries by continent for better organization
            continents = {
                'North America': ['US', 'CA', 'MX'],
                'South America': ['BR', 'AR', 'CL', 'CO', 'PE', 'VE'],
                'Europe': ['GB', 'DE', 'FR', 'IT', 'ES', 'NL', 'BE', 'CH', 'AT', 'SE', 'NO', 'DK', 'FI', 'PT', 'GR', 'IE', 'PL', 'CZ', 'HU', 'RO', 'BG', 'HR', 'RS', 'SK', 'SI', 'LT', 'LV', 'EE'],
                'Asia': ['RU', 'CN', 'JP', 'KR', 'IN', 'SG', 'TH', 'MY', 'ID', 'PH', 'VN', 'HK', 'TW', 'IL', 'TR', 'AE', 'SA', 'QA', 'PK', 'BD'],
                'Oceania': ['AU', 'NZ'],
                'Africa': ['ZA', 'EG', 'MA', 'NG', 'KE', 'DZ', 'TN']
            }
            
            # Create a panel for each continent
            for continent, codes in continents.items():
                # Filter countries that exist in our available countries
                continent_countries = {code: all_countries.get(code, code) for code in codes if code in all_countries}
                
                if continent_countries:
                    # Create table for this continent
                    table = Table(show_header=True, header_style="bold magenta")
                    table.add_column("Code", style="cyan", width=6)
                    table.add_column("Country", style="green")
                    
                    for code, name in sorted(continent_countries.items()):
                        table.add_row(code, name)
                    
                    # Add panel with table
                    panel = Panel(table, title=f"[bold blue]{continent}[/bold blue]", border_style="blue")
                    console.print(panel)
            
            # Add other countries that weren't in the continent groups
            other_countries = {code: name for code, name in all_countries.items() 
                             if not any(code in codes for codes in continents.values())}
            
            if other_countries:
                table = Table(show_header=True, header_style="bold magenta")
                table.add_column("Code", style="cyan", width=6)
                table.add_column("Country", style="green")
                
                for code, name in sorted(other_countries.items()):
                    table.add_row(code, name)
                
                panel = Panel(table, title="[bold blue]Other Countries[/bold blue]", border_style="blue")
                console.print(panel)
            
            # Add usage instructions
            usage_text = Text()
            usage_text.append("\nUsage: ", style="bold yellow")
            usage_text.append("proxy-finder fetch -c US -n 5\n", style="bold green")
            usage_text.append("This will fetch 5 proxies from the United States.\n\n", style="white")
            usage_text.append("For multiple countries: ", style="bold yellow")
            usage_text.append("proxy-finder fetch -c US,GB,DE -n 10\n", style="bold green")
            usage_text.append("This will fetch 10 proxies from the US, UK, and Germany.\n", style="white")
            
            console.print(Panel(usage_text, title="[bold red]How to Use Country Codes[/bold red]", border_style="red"))
            return
        
        # For other actions, create a proxy manager with country filter if specified
        # Handle multiple countries if provided with comma separation
        countries = None
        if args.country and ',' in args.country:
            countries = [c.strip().upper() for c in args.country.split(',')]
            # Use the first country for initial fetching
            country = countries[0] if countries else None
        else:
            country = args.country
            countries = [country] if country else None
            
        if country:
            # Use the new country-specific fetcher for better performance
            try:
                proxy_fetcher = CountryProxyFetcher(country_code=country, timeout=args.timeout)
                all_proxies = proxy_fetcher.fetch_proxies(max_proxies=args.number)
            except ValueError as e:
                console.print(f"[red]Error: {e}[/red]")
                console.print("[yellow]Valid country codes include:[/yellow]")
                console.print("[cyan]US (United States), GB (United Kingdom), DE (Germany), FR (France),[/cyan]")
                console.print("[cyan]JP (Japan), CA (Canada), AU (Australia), IN (India), etc.[/cyan]")
                sys.exit(1)
        else:
            # Use the regular fetcher for all countries
            proxy_manager = ProxyManager(timeout=args.timeout)
            all_proxies = proxy_manager.fetcher.fetch_proxies()
        
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
            with Progress() as progress:
                task = progress.add_task("[cyan]Validating proxy...", total=100)
                
                proxy_details = proxy_manager.get_proxy()
                progress.update(task, completed=100)
            
            if proxy_details:
                display_proxy_table([proxy_details], console)
            else:
                console.print("[red]No valid proxy found[/red]")
        
        elif args.action == 'rotate':
            # For rotate action, limit the number of proxies for faster results
            num_proxies = min(5, args.number)
            
            with Progress() as progress:
                task = progress.add_task(f"[cyan]Finding {num_proxies} proxies...", total=100)
                
                try:
                    # Use a more reasonable timeout for better success rate
                    proxy_manager.validator.timeout = min(8.0, args.timeout)
                    
                    # Get proxies with a timeout to prevent hanging
                    proxies = []
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
                console.print("[red]No valid proxies found. Try again or use different filters.[/red]")
    
    except Exception as e:
        logger.error(f"Error: {e}")
        sys.exit(1)

if __name__ == '__main__':
    main()
