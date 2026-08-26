"""CLI for BuildCipher Studio."""

import typer
from rich.console import Console
from rich.panel import Panel
from rich.markdown import Markdown
from rich.progress import Progress, SpinnerColumn, TextColumn
from typing import Optional
import sys

from cipher_genius.core.parser import RequirementParser
from cipher_genius.core.generator import SchemeGenerator
from cipher_genius.codegen.generator import CodeGenerator
from cipher_genius.knowledge.components import get_component_library

app = typer.Typer(
    name="buildcipher",
    help="BuildCipher: construction digital-asset trust and cryptographic strategy",
    add_completion=False,
)
console = Console()


@app.command()
def generate(
    requirement: str = typer.Argument(..., help="Natural language requirement description"),
    variants: int = typer.Option(1, "--variants", "-n", help="Number of scheme variants to generate"),
    output: Optional[str] = typer.Option(None, "--output", "-o", help="Output file path"),
    language: str = typer.Option("all", "--language", "-l", help="Code language: python, c, or all"),
):
    """
    Generate cryptographic scheme from natural language requirements
    """
    console.print(Panel.fit(
        "[bold blue]BuildCipher[/bold blue] - Construction Trust Strategy Agent",
        border_style="blue"
    ))

    try:
        # Step 1: Parse requirements
        console.print("\n[bold]Step 1:[/bold] Parsing requirements...")
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
        ) as progress:
            task = progress.add_task("Analyzing requirements...", total=None)

            parser = RequirementParser()
            parsed = parser.parse(requirement)

            progress.update(task, completed=True)

        # Show parsed requirements
        console.print("\n[green]✓[/green] Requirements parsed successfully!")
        console.print(f"[dim]Confidence: {parsed.confidence:.0%}[/dim]")

        if parsed.ambiguities:
            console.print("\n[yellow]⚠ Ambiguities:[/yellow]")
            for amb in parsed.ambiguities:
                console.print(f"  - {amb}")

        if parsed.assumptions:
            console.print("\n[yellow]ℹ Assumptions:[/yellow]")
            for assumption in parsed.assumptions:
                console.print(f"  - {assumption}")

        console.print(f"\n[bold]Requirement Summary:[/bold]")
        console.print(parsed.requirement.get_summary())

        # Step 2: Generate schemes
        console.print(f"\n[bold]Step 2:[/bold] Generating {variants} scheme variant(s)...")

        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
        ) as progress:
            task = progress.add_task(f"Generating schemes...", total=None)

            generator = SchemeGenerator()
            schemes = generator.generate(parsed.requirement, num_variants=variants)

            progress.update(task, completed=True)

        console.print(f"\n[green]✓[/green] Generated {len(schemes)} scheme(s)!")

        # Step 3: Generate code for each scheme
        console.print(f"\n[bold]Step 3:[/bold] Generating code implementations...")

        codegen = CodeGenerator()

        for i, scheme in enumerate(schemes, 1):
            console.print(f"\n[bold cyan]Scheme {i}: {scheme.metadata.name}[/bold cyan]")
            console.print(f"Score: {scheme.score}/10")

            # Show specification
            spec = scheme.get_specification()
            console.print(Panel(Markdown(spec), title="Specification", border_style="cyan"))

            # Generate code
            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                console=console,
            ) as progress:
                task = progress.add_task("Generating code...", total=None)

                implementation = codegen.generate_all(scheme)
                scheme.implementation = implementation

                progress.update(task, completed=True)

            # Display code
            if language in ["python", "all"]:
                console.print("\n[bold]Python Implementation:[/bold]")
                console.print(Panel(implementation.python, border_style="green"))

            if language in ["c", "all"]:
                console.print("\n[bold]C Implementation:[/bold]")
                console.print(Panel(implementation.c, border_style="yellow"))

            # Save to file if requested
            if output:
                output_file = output if variants == 1 else f"{output}.variant{i}.md"
                save_scheme_to_file(scheme, output_file)
                console.print(f"\n[green]✓[/green] Saved to: {output_file}")

        console.print(f"\n[bold green]✓ Complete![/bold green]")

    except KeyboardInterrupt:
        console.print("\n[yellow]Interrupted by user[/yellow]")
        raise typer.Exit(1)
    except Exception as e:
        console.print(f"\n[bold red]Error:[/bold red] {str(e)}")
        if "--debug" in sys.argv:
            raise
        raise typer.Exit(1)


@app.command()
def interactive():
    """
    Interactive mode for scheme generation
    """
    console.print(Panel.fit(
        "[bold blue]BuildCipher Interactive Mode[/bold blue]",
        border_style="blue"
    ))

    console.print("\nDescribe your cryptographic requirements in natural language.")
    console.print("[dim]Example: 'Lightweight encryption for IoT devices with 128-bit security'[/dim]\n")

    requirement = typer.prompt("Your requirement")

    variants = typer.prompt("Number of variants to generate", default=1, type=int)

    # Call generate command
    generate(requirement, variants=variants)


@app.command()
def components():
    """
    List available cryptographic components
    """
    console.print(Panel.fit(
        "[bold blue]Available Cryptographic Components[/bold blue]",
        border_style="blue"
    ))

    lib = get_component_library()

    console.print(f"\n{lib.get_summary()}")

    console.print("\n[bold]All Components:[/bold]")
    for comp in lib.list_all():
        console.print(f"\n[cyan]{comp.name}[/cyan] ({comp.category})")
        console.print(f"  Security: {comp.security.security_level}-bit")
        console.print(f"  Performance: {comp.performance.software_speed}")
        if comp.use_cases:
            console.print(f"  Use cases: {', '.join(comp.use_cases[:3])}")


@app.command()
def version():
    """Show version information"""
    from cipher_genius import __version__
    console.print(f"BuildCipher version {__version__}")


def save_scheme_to_file(scheme, filepath: str):
    """Save scheme to markdown file"""
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(f"# {scheme.metadata.name}\n\n")
        f.write(scheme.get_specification())
        f.write("\n\n## Design Rationale\n\n")
        f.write(scheme.design_rationale)

        if scheme.implementation.pseudocode:
            f.write("\n\n## Pseudocode\n\n```\n")
            f.write(scheme.implementation.pseudocode)
            f.write("\n```\n")

        if scheme.implementation.python:
            f.write("\n\n## Python Implementation\n\n```python\n")
            f.write(scheme.implementation.python)
            f.write("\n```\n")

        if scheme.implementation.c:
            f.write("\n\n## C Implementation\n\n```c\n")
            f.write(scheme.implementation.c)
            f.write("\n```\n")


if __name__ == "__main__":
    app()
