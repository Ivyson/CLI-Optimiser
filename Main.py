#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import subprocess
import logging
import re
import platform
from rich.console import Console
from rich.table import Table
from rich.panel import Panel

console = Console()
logging.basicConfig(
    filename="optimization.log",
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)

IS_MAC = platform.system() == "Darwin"
IS_WIN = platform.system() == "Windows"

def run_command(command):
    """Run shell commands and return the output."""
    try:
        result = subprocess.run(command, shell=True, text=True, capture_output=True)
        return result.stdout.strip()
    except Exception as e:
        logging.error(f"Error running command {command}: {e}")
        return None

def get_battery_health():
    if IS_MAC:
        max_capacity = run_command("ioreg -r -k MaxCapacity | grep 'MaxCapacity' | awk 'NR==1 {print $3}'")
        data_str = run_command("ioreg -r -k DesignCapacity | grep 'DesignCapacity' | awk 'NR==1 {print $0}'")
        match = re.search(r'"DesignCapacity"=(\d+)', data_str)
        if max_capacity and match:
            design_capacity = match.group(1)
            battery_health = (int(max_capacity) / int(design_capacity)) * 100
            return f"{battery_health:.2f}%"
        return "N/A"
    elif IS_WIN:
        try:
            import psutil
            battery = psutil.sensors_battery()
            if battery:
                return f"{battery.percent}%"
            else:
                return "N/A"
        except ImportError:
            return "psutil not installed"
    else:
        return "N/A"

def get_cache_size(path):
    if IS_MAC or IS_WIN:
        size = os.popen(f"du -sh {os.path.expanduser(path)} 2>/dev/null | awk '{{print $1}}'").read().strip() if IS_MAC else "N/A"
        return size if size else "0B"
    return "N/A"

def clear_browser_cache():
    """Clear browser cache and show freed space."""
    if IS_MAC:
        browser_cache_paths = {
            "Microsoft Edge": "~/Library/Caches/Microsoft Edge/*",
            "Safari": "~/Library/Caches/com.apple.Safari/*",
        }
    elif IS_WIN:
        browser_cache_paths = {
            "Edge": os.path.expandvars(r"%LOCALAPPDATA%\Microsoft\Edge\User Data\Default\Cache\*"),
            "Chrome": os.path.expandvars(r"%LOCALAPPDATA%\Google\Chrome\User Data\Default\Cache\*"),
        }
    else:
        browser_cache_paths = {}

    for browser, path in browser_cache_paths.items():
        try:
            size_before = get_cache_size(path)
            console.print(f"[cyan]{browser} cache size before cleanup: {size_before}[/cyan]")
            os.system(f"rm -rf {os.path.expanduser(path)}" if IS_MAC else f'del /q "{path}"')
            size_after = get_cache_size(path)
            console.print(f"[green]{browser} cache cleared! Current size: {size_after}[/green]")
        except Exception as e:
            console.print(f"[red]Error clearing {browser} cache: {e}[/red]")

def clear_cache():
    """Clear system caches."""
    if IS_MAC:
        cache_paths = ["~/Library/Caches", "/Library/Caches"]
    elif IS_WIN:
        cache_paths = [os.path.expandvars(r"%TEMP%"), os.path.expandvars(r"C:\Windows\Temp")]
    else:
        cache_paths = []
    total_freed = 0
    try:
        with console.status("[cyan]Clearing cache...") as status:
            for path in cache_paths:
                expanded_path = os.path.expanduser(path)
                before_size = run_command(f"du -sm {expanded_path} 2>/dev/null | awk '{{print $1}}'") if IS_MAC else None
                os.system(f"rm -rf {expanded_path}/*" if IS_MAC else f'del /q /s "{expanded_path}\\*"')
                clear_browser_cache()
                after_size = run_command(f"du -sm {expanded_path} 2>/dev/null | awk '{{print $1}}'") if IS_MAC else None
                if before_size and after_size:
                    freed = int(before_size) - int(after_size)
                    total_freed += freed
                    console.print(f"Freed [green]{freed} MB[/green] from {path}")
    except Exception as e:
        console.print(f"[red]Error clearing cache: {e}[/red]")

def check_system_updates():
    """Check for system updates and manage Homebrew/Chocolatey/Winget packages."""
    try:
        # Gather info with spinner
        with console.status("[bold blue]Checking the system's integrity[/bold blue]"):
            brew_exists = None
            choco_exists = None
            winget_exists = None
            system_updates = None
            outdated_list = []
            pkg_mgr = None
            # For Linux, You can add your package manager checks here and perform teh operations using it..

            if IS_MAC:
                brew_exists = run_command("which brew")
                system_updates = run_command("softwareupdate -l")
                if brew_exists:
                    brew_outdated = run_command("brew outdated")
                    outdated_list = brew_outdated.splitlines() if brew_outdated else []
            elif IS_WIN:
                choco_exists = run_command("where choco")
                winget_exists = run_command("where winget")
                if choco_exists:
                    pkg_mgr = "choco"
                    choco_outdated = run_command("choco outdated")
                    outdated_list = [line.split()[0] for line in choco_outdated.splitlines()[1:] if line.strip()] if choco_outdated else []
                elif winget_exists:
                    pkg_mgr = "winget"
                    winget_outdated = run_command("winget upgrade")
                    lines = winget_outdated.splitlines()
                    if len(lines) > 1:
                        header_idx = 0
                        for i, l in enumerate(lines):
                            if l.strip().startswith("Name"):
                                header_idx = i
                                break
                        outdated_list = [l.split()[1] for l in lines[header_idx+1:] if l.strip()]
            # else: leave all as empty

        # Spinner ends here, now interact with user
        if IS_MAC:
            if system_updates:
                console.print(f"[yellow]System updates available:\n{system_updates}[/yellow]")
            else:
                console.print("[green]Your macOS is up to date.[/green]")

            if not brew_exists:
                console.print("[red]Homebrew is not installed. Skipping Homebrew updates.[/red]")
            elif outdated_list:
                table = Table(title="Outdated Homebrew Packages (showing up to 5)", header_style="bold magenta")
                table.add_column("#", justify="right")
                table.add_column("Package", justify="left")
                for idx, pkg in enumerate(outdated_list[:5], 1):
                    table.add_row(str(idx), pkg)
                console.print(table)
                console.print(f"[yellow]Total outdated packages: {len(outdated_list)}[/yellow]")

                if len(outdated_list) > 5:
                    see_all = console.input("[cyan]See all outdated packages? (y/n): [/cyan]").strip().lower()
                    if see_all == "y":
                        full_table = Table(title="All Outdated Homebrew Packages", header_style="bold magenta")
                        full_table.add_column("#", justify="right")
                        full_table.add_column("Package", justify="left")
                        for idx, pkg in enumerate(outdated_list, 1):
                            full_table.add_row(str(idx), pkg)
                        console.print(full_table)

                upgrade_choice = console.input(
                    "[cyan]Enter numbers to upgrade (comma separated), 'a' for all, or 'n' to skip: [/cyan]"
                ).strip().lower()
                if upgrade_choice == "a":
                    with console.status("[yellow]Upgrading all outdated packages...[/yellow]"):
                        os.system("brew upgrade > /dev/null 2>&1")
                    console.print("[green]All packages upgraded![/green]")
                elif upgrade_choice == "n":
                    console.print("[green]No packages upgraded.[/green]")
                else:
                    try:
                        indices = [int(i.strip()) for i in upgrade_choice.split(",") if i.strip().isdigit()]
                        selected_pkgs = [outdated_list[i-1] for i in indices if 0 < i <= len(outdated_list)]
                        if selected_pkgs:
                            for pkg in selected_pkgs:
                                with console.status(f"[yellow]Installing {pkg}...[/yellow]"):
                                    os.system(f"brew upgrade {pkg} > /dev/null 2>&1")
                                console.print(f"[green]{pkg} upgraded![/green]")
                            console.print("[green]Selected packages upgraded![/green]")
                        else:
                            console.print("[red]No valid packages selected.[/red]")
                    except Exception as e:
                        console.print(f"[red]Error parsing selection: {e}[/red]")
            else:
                if brew_exists:
                    console.print("[green]Homebrew is up to date.[/green]")

        elif IS_WIN:
            if not (choco_exists or winget_exists):
                console.print("[red]Neither Chocolatey nor Winget is installed. Skipping package updates.[/red]")
            elif not pkg_mgr or not outdated_list:
                if pkg_mgr:
                    console.print(f"[green]{pkg_mgr.capitalize()} is up to date.[/green]")
                else:
                    console.print("[yellow]No package manager detected for updates.[/yellow]")
            else:
                try:
                    table = Table(title=f"Outdated {pkg_mgr.capitalize()} Packages (showing up to 5)", header_style="bold magenta")
                    table.add_column("#", justify="right")
                    table.add_column("Package", justify="left")
                    for idx, pkg in enumerate(outdated_list[:5], 1):
                        table.add_row(str(idx), pkg)
                    console.print(table)
                    console.print(f"[yellow]Total outdated packages: {len(outdated_list)}[/yellow]")

                    if len(outdated_list) > 5:
                        see_all = console.input("[cyan]See all outdated packages? (y/n): [/cyan]").strip().lower()
                        if see_all == "y":
                            full_table = Table(title=f"All Outdated {pkg_mgr.capitalize()} Packages", header_style="bold magenta")
                            full_table.add_column("#", justify="right")
                            full_table.add_column("Package", justify="left")
                            for idx, pkg in enumerate(outdated_list, 1):
                                full_table.add_row(str(idx), pkg)
                            console.print(full_table)

                    upgrade_choice = console.input(
                        f"[cyan]Enter numbers to upgrade (comma separated), 'a' for all, or 'n' to skip: [/cyan]"
                    ).strip().lower()
                    if upgrade_choice == "a":
                        with console.status(f"[yellow]Upgrading all outdated {pkg_mgr} packages...[/yellow]"):
                            if pkg_mgr == "choco":
                                os.system("choco upgrade all -y > NUL 2>&1")
                            elif pkg_mgr == "winget":
                                os.system("winget upgrade --all --silent > NUL 2>&1")
                        console.print(f"[green]All {pkg_mgr} packages upgraded![/green]")
                    elif upgrade_choice == "n":
                        console.print("[green]No packages upgraded.[/green]")
                    else:
                        try:
                            indices = [int(i.strip()) for i in upgrade_choice.split(",") if i.strip().isdigit()]
                            selected_pkgs = [outdated_list[i-1] for i in indices if 0 < i <= len(outdated_list)]
                            if selected_pkgs:
                                for pkg in selected_pkgs:
                                    with console.status(f"[yellow]Upgrading {pkg}...[/yellow]"):
                                        if pkg_mgr == "choco":
                                            os.system(f"choco upgrade {pkg} -y > NUL 2>&1")
                                        elif pkg_mgr == "winget":
                                            os.system(f"winget upgrade --id {pkg} --silent > NUL 2>&1")
                                    console.print(f"[green]{pkg} upgraded![/green]")
                                console.print("[green]Selected packages upgraded![/green]")
                            else:
                                console.print("[red]No valid packages selected.[/red]")
                        except Exception as e:
                            console.print(f"[red]Error parsing selection: {e}[/red]")
                except Exception as e:
                    console.print(f"[red]Error displaying or upgrading packages: {e}[/red]")
            console.print("[yellow]Please check Windows Update in Settings manually.[/yellow]")

    except Exception as e:
        console.print(f"[red]Failed to check system updates: {e}[/red]")
        logging.error(f"Failed to check system updates: {e}")

def system_summary():
    """Display system diagnostic summary."""
    try:
        with console.status("[bold blue]Loading System Summary[/bold blue]") as status:
            if IS_MAC:
                uptime = run_command("uptime | awk -F', ' '{print $1}'")
                free_disk = run_command("df -h / | awk 'NR==2 {print $4}'")
                free_ram = run_command('vm_stat | grep "Pages free" | awk \'{print $3}\' | sed \'s/\\.//\' | awk \'{printf \"%.1f MB\", $1 * 4 / 1024}\'')
                battery_health = get_battery_health()
                cpu_temp = run_command("istats cpu temp | grep 'CPU temp' | awk '{print $3}'")
            elif IS_WIN:
                uptime = run_command("net stats workstation | findstr 'since'")
                free_disk = run_command("wmic logicaldisk get size,freespace,caption")# That is if it exists..
                free_ram = run_command("wmic OS get FreePhysicalMemory")
                battery_health = get_battery_health()
                cpu_temp = "N/A"  # Needs 3rd party tools on Windows
            else:
                uptime = free_disk = free_ram = battery_health = cpu_temp = "N/A"

            table = Table(show_header=True, header_style="bold magenta")
            table.add_column("Metric", justify="left", style="cyan")
            table.add_column("Value", justify="right", style="green")

            table.add_row("Uptime", uptime)
            table.add_row("Free Disk Space", free_disk)
            table.add_row("Free RAM", free_ram)
            table.add_row("Battery Health", battery_health)
            table.add_row("CPU Temperature", cpu_temp)

            console.print(table)
    except Exception as e:
        console.print(f"[red] Failed to display the System stats due to error : {e}")

def monitor_usage():
    """Monitor resource usage and allow user to kill processes."""
    try:
        # Only show spinner while gathering stats
        with console.status("[bold yellow]Monitoring Resource Usage...[/bold yellow]"):
            if IS_MAC:
                cpu_stats = run_command("ps aux | sort -nrk 3,3 | head -n 10")
                mem_stats = run_command("ps aux | sort -nrk 4,4 | head -n 10")
            elif IS_WIN:
                cpu_stats = run_command('wmic path Win32_PerfFormattedData_PerfProc_Process get Name,IDProcess,PercentProcessorTime | findstr /v "0"')
                mem_stats = run_command('wmic process get name,processid,workingsetsize | sort /r /+2 | more')
            else:
                cpu_stats = mem_stats = ""

        # Spinner ends here, now process and display
        cpu_list = []
        mem_list = []

        cpu_table = Table(title="Top CPU Consumers", header_style="bold red")
        cpu_table.add_column("#", justify="right")
        cpu_table.add_column("PID", justify="right")
        cpu_table.add_column("Process", justify="left")
        cpu_table.add_column("CPU (%)", justify="right")

        mem_table = Table(title="Top Memory Consumers", header_style="bold blue")
        mem_table.add_column("#", justify="right")
        mem_table.add_column("PID", justify="right")
        mem_table.add_column("Process", justify="left")
        mem_table.add_column("Memory", justify="right")

        if IS_MAC:
            for idx, line in enumerate(cpu_stats.splitlines()):
                parts = line.split()
                if len(parts) > 10:
                    cpu_list.append((parts[1], parts[10]))  # PID, Command
                    cpu_table.add_row(str(idx+1), parts[1], parts[10], parts[2])
            for idx, line in enumerate(mem_stats.splitlines()):
                parts = line.split()
                if len(parts) > 10:
                    mem_list.append((parts[1], parts[10]))  # PID, Command
                    mem_table.add_row(str(idx+1), parts[1], parts[10], parts[3])
        elif IS_WIN:
            for idx, line in enumerate(cpu_stats.splitlines()):
                parts = line.split()
                if len(parts) >= 3 and parts[1].isdigit():
                    cpu_list.append((parts[1], parts[0]))  # PID, Name
                    cpu_table.add_row(str(idx+1), parts[1], parts[0], parts[2])
            for idx, line in enumerate(mem_stats.splitlines()):
                parts = line.split()
                if len(parts) >= 3 and parts[1].isdigit():
                    mem_list.append((parts[1], parts[0]))  # PID, Name
                    mem_table.add_row(str(idx+1), parts[1], parts[0], parts[2])

        parent_table = Table(title="System Resource Usage", header_style="bold green")
        parent_table.add_column("CPU Usage", justify="center")
        parent_table.add_column("Memory Usage", justify="center")
        parent_table.add_row(cpu_table, mem_table)
        console.print(parent_table)

        # Ask user if they want to kill a processes
        console.print("\n[bold yellow]Select a process to kill:[/bold yellow]")
        console.print("1. Kill a CPU-intensive process")
        console.print("2. Kill a Memory-intensive process")
        console.print("3. Cancel")
        action = console.input("[cyan]Enter choice (1/2/3): [/cyan]")

        if action == "1" and cpu_list:
            idx = console.input(f"Enter number (1-{len(cpu_list)}): ")
            if idx.isdigit() and 1 <= int(idx) <= len(cpu_list):
                pid = cpu_list[int(idx)-1][0]
                kill_process(pid)
        elif action == "2" and mem_list:
            idx = console.input(f"Enter number (1-{len(mem_list)}): ")
            if idx.isdigit() and 1 <= int(idx) <= len(mem_list):
                pid = mem_list[int(idx)-1][0]
                kill_process(pid)
        else:
            console.print("[green]No process killed.[/green]")

    except Exception as e:
        console.print(f'[red] Failed to check the system usage : {e}')

def kill_process(pid):
    """Kill a process by PID."""
    try:
        if IS_WIN:
            os.system(f"taskkill /PID {pid} /F")
        else:
            os.system(f"kill -9 {pid}")
        console.print(f"[bold red]Process {pid} killed.[/bold red]")
    except Exception as e:
        console.print(f"[red]Failed to kill process {pid}: {e}[/red]")

def display_menu():
    """Display the main menu."""
    menu = Panel(
        "[bold blue]Mac/Windows Optimization Utility[/bold blue]\n\n"
        "1. System Check\n"
        "2. Clear Cache\n"
        "3. Monitor Resource Usage\n"
        "4. Check for Updates\n"
        "5. Exit\n",
        title="[bold magenta]Main Menu[/bold magenta]",
    )
    console.print(menu)

if __name__ == "__main__":
    while True:
        try:
            display_menu()
            choice = console.input("[bold cyan]Choose an option: [/bold cyan]")

            if choice == "1":
                system_summary()
            elif choice == "2":
                clear_cache()
            elif choice == "3":
                monitor_usage()
            elif choice == "4":
                check_system_updates()
            elif choice == "5":
                console.print("[bold red]Exiting...[/bold red]")
                break
            else:
                console.print("[bold red]Invalid choice, please try again.[/bold red]")
        except KeyboardInterrupt:
            console.print("\n[bold red]Interrupted by user. Exiting...[/bold red]")
            break
        except Exception as e:
            console.print(f"[red]An error occurred: {e}[/red]")
