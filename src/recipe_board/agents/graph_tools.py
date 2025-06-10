"""
Tools for creating dependency graph visualizations from recipe data.
"""

import plotly.graph_objects as go
from typing import Dict, List, Tuple, Any
import math
import os
from ..core.state import RecipeSessionState
from wasabi import msg


def _detect_dark_mode() -> bool:
    """
    Detect if dark mode should be used based on environment or system settings.
    """
    # Check environment variable first
    dark_mode_env = os.getenv("GRADIO_THEME", "").lower()
    if "dark" in dark_mode_env:
        return True

    # Try to detect system dark mode (macOS)
    try:
        import subprocess

        result = subprocess.run(
            ["defaults", "read", "-g", "AppleInterfaceStyle"],
            capture_output=True,
            text=True,
            timeout=2,
        )
        if result.returncode == 0 and "dark" in result.stdout.lower():
            return True
    except (subprocess.TimeoutExpired, FileNotFoundError, Exception):
        pass

    return False


def _get_theme_colors(dark_mode: bool) -> Dict[str, str]:
    """
    Get color scheme based on theme mode.
    """
    if dark_mode:
        return {
            "background": "#2F2F2F",
            "text": "#FFFFFF",
            "annotation_text": "#CCCCCC",
            "edges": "#666666",
            "ingredients": "#00FF7F",  # Bright green
            "equipment": "#FF6347",  # Tomato (better for dark)
            "actions": "#87CEEB",  # Sky blue (better for dark)
        }
    else:
        return {
            "background": "white",
            "text": "#000000",
            "annotation_text": "gray",
            "edges": "#888888",
            "ingredients": "#00FF7F",  # Spring green
            "equipment": "#FF4500",  # Orange red
            "actions": "#1E90FF",  # Dodger blue
        }


def create_dependency_graph(
    state: RecipeSessionState, dark_mode: bool = None
) -> go.Figure:
    """
    Create a network dependency graph from recipe state.

    Uses a tripartite graph structure:
    - Ingredient nodes (green circles)
    - Action nodes (blue diamonds)
    - Equipment nodes (orange squares)
    - Edges connect ingredients → actions and actions → equipment

    Args:
        state: RecipeSessionState with parsed ingredients, equipment, and actions
        dark_mode: Whether to use dark mode colors. If None, auto-detect from system.

    Returns:
        Plotly Figure object with interactive network graph
    """
    # Auto-detect dark mode if not specified
    if dark_mode is None:
        dark_mode = _detect_dark_mode()

    # Get theme colors
    colors = _get_theme_colors(dark_mode)
    if not state.actions:
        # Return empty figure with message
        fig = go.Figure()
        fig.add_annotation(
            text="No actions found. Parse recipe actions first to generate dependency graph.",
            xref="paper",
            yref="paper",
            x=0.5,
            y=0.5,
            xanchor="center",
            yanchor="middle",
            showarrow=False,
            font=dict(size=16, color=colors["annotation_text"]),
        )
        fig.update_layout(
            title="Recipe Dependency Graph",
            showlegend=False,
            xaxis={"visible": False},
            yaxis={"visible": False},
            plot_bgcolor=colors["background"],
        )
        return fig

    # Build node and edge data
    nodes, edges = _build_graph_data(state, colors)

    # Calculate node positions using force-directed layout
    node_positions = _calculate_force_directed_positions(nodes, edges)

    # Create edge traces
    edge_traces = _create_edge_traces(edges, node_positions, colors)

    # Create node traces by type
    node_traces = _create_node_traces(nodes, node_positions)

    # Combine all traces
    fig_data = edge_traces + node_traces

    # Configure layout
    fig = go.Figure(data=fig_data)
    fig.update_layout(
        title=dict(
            text="Recipe Dependency Graph", font=dict(size=18, color=colors["text"])
        ),
        showlegend=True,
        hovermode="closest",
        dragmode="pan",
        margin=dict(b=20, l=5, r=5, t=40),
        paper_bgcolor=colors["background"],
        font=dict(color=colors["text"]),
        annotations=[
            dict(
                text="Hover over nodes for details. Drag to explore the network.",
                showarrow=False,
                xref="paper",
                yref="paper",
                x=0.005,
                y=-0.002,
                xanchor="left",
                yanchor="bottom",
                font=dict(color=colors["annotation_text"], size=12),
            )
        ],
        xaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
        yaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
        plot_bgcolor=colors["background"],
    )

    return fig


def _build_graph_data(
    state: RecipeSessionState, colors: Dict[str, str]
) -> Tuple[List[Dict], List[Dict]]:
    """Build nodes and edges data structures from recipe state."""
    nodes = []
    edges = []

    # Create ingredient nodes
    for ingredient in state.ingredients:
        nodes.append(
            {
                "id": ingredient.id,
                "name": ingredient.name,
                "type": "ingredient",
                "size": 35,
                "color": colors["ingredients"],
                "symbol": "circle",
                "hover_text": _format_ingredient_hover(ingredient),
            }
        )

    # Create equipment nodes
    for equipment in state.equipment:
        nodes.append(
            {
                "id": equipment.id,
                "name": equipment.name,
                "type": "equipment",
                "size": 40,
                "color": colors["equipment"],
                "symbol": "square",
                "hover_text": _format_equipment_hover(equipment),
            }
        )

    # Create action nodes and edges
    for action in state.actions:
        action_node_id = f"action_{action.id}"
        nodes.append(
            {
                "id": action_node_id,
                "name": action.name,
                "type": "action",
                "size": 45,
                "color": colors["actions"],
                "symbol": "diamond",
                "hover_text": _format_action_hover(action, state),
            }
        )

        # Create edges from ingredients to action
        for ingredient_id in action.ingredient_ids:
            edges.append(
                {
                    "source": ingredient_id,
                    "target": action_node_id,
                    "type": "ingredient_to_action",
                }
            )

        # Create edge from action to equipment
        if action.equipment_id:
            edges.append(
                {
                    "source": action_node_id,
                    "target": action.equipment_id,
                    "type": "action_to_equipment",
                }
            )

    return nodes, edges


def _format_ingredient_hover(ingredient) -> str:
    """Format hover text for ingredient nodes."""
    parts = [f"<b>{ingredient.name}</b>"]
    if ingredient.amount:
        amount_text = f"{ingredient.amount}"
        if ingredient.unit:
            amount_text += f" {ingredient.unit}"
        parts.append(f"Amount: {amount_text}")
    if ingredient.modifiers:
        parts.append(f"Modifiers: {', '.join(ingredient.modifiers)}")
    return "<br>".join(parts)


def _format_equipment_hover(equipment) -> str:
    """Format hover text for equipment nodes."""
    parts = [f"<b>{equipment.name}</b>"]
    parts.append(f"Required: {'Yes' if equipment.required else 'No'}")
    if equipment.modifiers:
        parts.append(f"Modifiers: {equipment.modifiers}")
    return "<br>".join(parts)


def _format_action_hover(action, state: RecipeSessionState) -> str:
    """Format hover text for action nodes."""
    parts = [f"<b>Action: {action.name}</b>"]

    # Find ingredient names
    if action.ingredient_ids:
        ingredient_names = [
            ing.name for ing in state.ingredients if ing.id in action.ingredient_ids
        ]
        if ingredient_names:
            parts.append(f"Ingredients: {', '.join(ingredient_names)}")

    # Find equipment name
    if action.equipment_id:
        equipment_name = next(
            (eq.name for eq in state.equipment if eq.id == action.equipment_id),
            "Unknown",
        )
        parts.append(f"Equipment: {equipment_name}")

    return "<br>".join(parts)


def _calculate_force_directed_positions(
    nodes: List[Dict], edges: List[Dict]
) -> Dict[str, Tuple[float, float]]:
    """Calculate node positions using simple force-directed algorithm."""
    node_positions = {}
    node_count = len(nodes)

    if node_count == 0:
        return node_positions

    # Initialize positions in a circle
    for i, node in enumerate(nodes):
        angle = 2 * math.pi * i / node_count
        radius = max(1.0, node_count / 6)  # Scale radius with node count
        x = radius * math.cos(angle)
        y = radius * math.sin(angle)
        node_positions[node["id"]] = (x, y)

    # Simple force-directed adjustment
    for iteration in range(50):  # Limited iterations for performance
        forces = {node_id: [0.0, 0.0] for node_id in node_positions}

        # Repulsive forces between all nodes
        for i, node1 in enumerate(nodes):
            for j, node2 in enumerate(nodes):
                if i >= j:
                    continue

                x1, y1 = node_positions[node1["id"]]
                x2, y2 = node_positions[node2["id"]]

                dx = x2 - x1
                dy = y2 - y1
                distance = max(0.1, math.sqrt(dx * dx + dy * dy))

                # Repulsive force
                force_magnitude = 0.1 / (distance * distance)
                fx = force_magnitude * dx / distance
                fy = force_magnitude * dy / distance

                forces[node1["id"]][0] -= fx
                forces[node1["id"]][1] -= fy
                forces[node2["id"]][0] += fx
                forces[node2["id"]][1] += fy

        # Attractive forces for connected nodes
        for edge in edges:
            source_id = edge["source"]
            target_id = edge["target"]

            if source_id not in node_positions or target_id not in node_positions:
                continue

            x1, y1 = node_positions[source_id]
            x2, y2 = node_positions[target_id]

            dx = x2 - x1
            dy = y2 - y1
            distance = max(0.1, math.sqrt(dx * dx + dy * dy))

            # Attractive force
            force_magnitude = 0.02 * distance
            fx = force_magnitude * dx / distance
            fy = force_magnitude * dy / distance

            forces[source_id][0] += fx
            forces[source_id][1] += fy
            forces[target_id][0] -= fx
            forces[target_id][1] -= fy

        # Apply forces
        for node_id in node_positions:
            x, y = node_positions[node_id]
            fx, fy = forces[node_id]

            # Damping factor
            damping = 0.1
            x += fx * damping
            y += fy * damping

            node_positions[node_id] = (x, y)

    return node_positions


def _create_edge_traces(
    edges: List[Dict],
    node_positions: Dict[str, Tuple[float, float]],
    colors: Dict[str, str],
) -> List[go.Scatter]:
    """Create edge traces for the graph."""
    edge_x = []
    edge_y = []

    for edge in edges:
        source_id = edge["source"]
        target_id = edge["target"]

        if source_id in node_positions and target_id in node_positions:
            x0, y0 = node_positions[source_id]
            x1, y1 = node_positions[target_id]

            edge_x.extend([x0, x1, None])
            edge_y.extend([y0, y1, None])

    edge_trace = go.Scatter(
        x=edge_x,
        y=edge_y,
        line=dict(width=3, color=colors["edges"]),
        hoverinfo="none",
        mode="lines",
        showlegend=False,
    )

    return [edge_trace]


def _create_node_traces(
    nodes: List[Dict], node_positions: Dict[str, Tuple[float, float]]
) -> List[go.Scatter]:
    """Create node traces grouped by type."""
    traces = []

    # Group nodes by type
    node_types = {"ingredient": [], "action": [], "equipment": []}
    for node in nodes:
        node_type = node["type"]
        if node_type in node_types:
            node_types[node_type].append(node)

    # Create trace for each node type
    type_configs = {
        "ingredient": {"name": "Ingredients", "symbol": "circle"},
        "action": {"name": "Actions", "symbol": "diamond"},
        "equipment": {"name": "Equipment", "symbol": "square"},
    }

    for node_type, type_nodes in node_types.items():
        if not type_nodes:
            continue

        config = type_configs[node_type]

        # Extract data for this node type
        x_vals = []
        y_vals = []
        texts = []
        hovers = []
        colors = []
        sizes = []

        for node in type_nodes:
            if node["id"] in node_positions:
                x, y = node_positions[node["id"]]
                x_vals.append(x)
                y_vals.append(y)
                texts.append(node["name"])
                hovers.append(node["hover_text"])
                colors.append(node["color"])
                sizes.append(node["size"])

        if x_vals:  # Only create trace if we have data
            trace = go.Scatter(
                x=x_vals,
                y=y_vals,
                mode="markers+text",
                name=config["name"],
                text=texts,
                textposition="middle center",
                textfont=dict(size=12, color="white", family="Arial Black"),
                hoverinfo="text",
                hovertext=hovers,
                marker=dict(
                    symbol=config["symbol"],
                    size=sizes,
                    color=(
                        colors[0] if colors else "#888"
                    ),  # Use consistent color per type
                    line=dict(width=3, color="white"),
                ),
            )
            traces.append(trace)

    return traces


def generate_graph_download_data(fig: go.Figure) -> Dict[str, Any]:
    """
    Generate data for downloading the graph in various formats.

    Args:
        fig: Plotly figure object

    Returns:
        Dictionary with download options and data
    """
    try:
        # Generate different format options
        download_data = {
            "html": fig.to_html(include_plotlyjs=True),
            "json": fig.to_json(),
            "png_available": True,  # Plotly supports PNG export
            "svg_available": True,  # Plotly supports SVG export
        }

        msg.info("Graph download data generated successfully")
        return download_data

    except Exception as e:
        msg.warn(f"Error generating download data: {e}")
        return {
            "html": None,
            "json": None,
            "png_available": False,
            "svg_available": False,
        }
