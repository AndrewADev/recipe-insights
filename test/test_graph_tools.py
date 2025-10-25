"""
Unit tests for graph visualization tools.
"""

import plotly.graph_objects as go
from recipe_board.agents.graph_tools import (
    create_dependency_graph,
    generate_graph_download_data,
    _build_graph_data,
    _calculate_force_directed_positions,
    _format_ingredient_hover,
    _format_equipment_hover,
    _format_action_hover,
    _get_theme_colors,
)
from recipe_board.core.state import RecipeSessionState
from recipe_board.core.recipe import Ingredient, Equipment, Action


class TestCreateDependencyGraph:
    """Test suite for create_dependency_graph function."""

    def test_empty_actions_returns_message_figure(self):
        """Test that empty actions returns a figure with informational message."""
        state = RecipeSessionState()
        state.ingredients = [
            Ingredient(name="flour", amount=2.0, unit="cups", modifiers=[], raw_text="2 cups flour")
        ]
        state.equipment = [
            Equipment(name="bowl", required=True, modifiers=None)
        ]
        # No actions

        fig = create_dependency_graph(state)

        assert isinstance(fig, go.Figure)
        # Should have annotation with message about no actions
        assert len(fig.layout.annotations) > 0
        assert "No actions found" in fig.layout.annotations[0].text

    def test_with_actions_creates_network_graph(self, multi_ingredient_state):
        """Test that valid state with actions creates proper network graph."""
        fig = create_dependency_graph(multi_ingredient_state)

        assert isinstance(fig, go.Figure)
        assert len(fig.data) > 0  # Should have traces for nodes and edges
        assert fig.layout.title.text == "Recipe Dependency Graph"

    def test_graph_has_proper_traces(self, basic_recipe_state):
        """Test that graph contains expected node and edge traces."""
        fig = create_dependency_graph(basic_recipe_state)

        # Should have edge trace plus node traces (ingredients, actions, equipment)
        assert len(fig.data) >= 2  # At least edges + some node traces

        # Check for different trace types
        trace_names = [trace.name for trace in fig.data if hasattr(trace, 'name') and trace.name]
        expected_traces = ['Ingredients', 'Actions', 'Equipment']

        # At least some of these should be present
        found_traces = [name for name in expected_traces if name in trace_names]
        assert len(found_traces) > 0


class TestBuildGraphData:
    """Test suite for _build_graph_data function."""

    def test_empty_state_returns_empty_data(self):
        """Test that empty state returns empty nodes and edges."""
        state = RecipeSessionState()
        colors = _get_theme_colors(False)

        nodes, edges = _build_graph_data(state, colors)

        assert nodes == []
        assert edges == []

    def test_ingredients_become_nodes(self, basic_ingredient):
        """Test that ingredients are converted to nodes properly."""
        state = RecipeSessionState()
        state.ingredients = [basic_ingredient]
        colors = _get_theme_colors(False)

        nodes, edges = _build_graph_data(state, colors)

        assert len(nodes) == 1
        node = nodes[0]
        assert node['id'] == basic_ingredient.id
        assert node['name'] == "flour"
        assert node['type'] == 'ingredient'
        assert node['color'] == colors['ingredients']
        assert "flour" in node['hover_text']

    def test_equipment_becomes_nodes(self, basic_equipment):
        """Test that equipment is converted to nodes properly."""
        state = RecipeSessionState()
        state.equipment = [basic_equipment]
        colors = _get_theme_colors(False)

        nodes, _ = _build_graph_data(state, colors)

        assert len(nodes) == 1
        node = nodes[0]
        assert node['id'] == basic_equipment.id
        assert node['name'] == "bowl"
        assert node['type'] == 'equipment'
        assert node['color'] == colors['equipment']

    def test_actions_create_nodes_and_edges(self, basic_recipe_state):
        """Test that actions create action nodes and connecting edges."""
        colors = _get_theme_colors(False)

        nodes, edges = _build_graph_data(basic_recipe_state, colors)

        ingredient = basic_recipe_state.ingredients[0]
        equipment = basic_recipe_state.equipment[0]

        # Should have 3 nodes: ingredient, equipment, action
        assert len(nodes) == 3

        # Find action node
        action_nodes = [n for n in nodes if n['type'] == 'action']
        assert len(action_nodes) == 1
        action_node = action_nodes[0]
        assert action_node['name'] == "mix"
        assert action_node['color'] == colors['actions']

        # Should have 2 edges: ingredient->action, action->equipment
        assert len(edges) == 2

        # Check edge connections
        ingredient_to_action = next((e for e in edges if e['source'] == ingredient.id), None)
        assert ingredient_to_action is not None
        assert ingredient_to_action['target'] == action_node['id']
        assert ingredient_to_action['type'] == 'ingredient_to_action'

        action_to_equipment = next((e for e in edges if e['source'] == action_node['id']), None)
        assert action_to_equipment is not None
        assert action_to_equipment['target'] == equipment.id
        assert action_to_equipment['type'] == 'action_to_equipment'


class TestHoverTextFormatting:
    """Test suite for hover text formatting functions."""

    def test_format_ingredient_hover_complete(self):
        """Test ingredient hover formatting with all fields."""
        ingredient = Ingredient(
            name="flour",
            amount=2.5,
            unit="cups",
            modifiers=["all-purpose", "sifted"],
            raw_text="2.5 cups flour"
        )

        hover_text = _format_ingredient_hover(ingredient)

        assert "<b>flour</b>" in hover_text
        assert "Amount: 2.5 cups" in hover_text
        assert "Modifiers: all-purpose, sifted" in hover_text

    def test_format_ingredient_hover_minimal(self):
        """Test ingredient hover formatting with minimal fields."""
        ingredient = Ingredient(name="salt", amount=None, unit=None, modifiers=[], raw_text="salt")

        hover_text = _format_ingredient_hover(ingredient)

        assert "<b>salt</b>" in hover_text
        assert "Amount:" not in hover_text
        assert "Modifiers:" not in hover_text

    def test_format_equipment_hover(self):
        """Test equipment hover formatting."""
        equipment = Equipment(name="mixing bowl", required=True, modifiers="large")

        hover_text = _format_equipment_hover(equipment)

        assert "<b>mixing bowl</b>" in hover_text
        assert "Required: Yes" in hover_text
        assert "Modifiers: large" in hover_text

    def test_format_equipment_hover_not_required(self):
        """Test equipment hover formatting when not required."""
        equipment = Equipment(name="whisk", required=False, modifiers=None)

        hover_text = _format_equipment_hover(equipment)

        assert "<b>whisk</b>" in hover_text
        assert "Required: No" in hover_text
        assert "Modifiers:" not in hover_text

    def test_format_action_hover(self, multi_ingredient_state):
        """Test action hover formatting."""
        action = multi_ingredient_state.actions[0]

        hover_text = _format_action_hover(action, multi_ingredient_state)

        assert "<b>Action: mix</b>" in hover_text
        assert "Ingredients: flour, salt" in hover_text
        assert "Equipment: mixing bowl" in hover_text


class TestForceDirectedPositions:
    """Test suite for _calculate_force_directed_positions function."""

    def test_empty_nodes_returns_empty_positions(self):
        """Test that empty nodes list returns empty positions."""
        positions = _calculate_force_directed_positions([], [])
        assert positions == {}

    def test_single_node_has_position(self):
        """Test that single node gets a position."""
        nodes = [{'id': 'node1', 'name': 'test'}]
        edges = []

        positions = _calculate_force_directed_positions(nodes, edges)

        assert 'node1' in positions
        x, y = positions['node1']
        assert isinstance(x, (int, float))
        assert isinstance(y, (int, float))

    def test_multiple_nodes_have_different_positions(self):
        """Test that multiple nodes get different positions."""
        nodes = [
            {'id': 'node1', 'name': 'test1'},
            {'id': 'node2', 'name': 'test2'},
            {'id': 'node3', 'name': 'test3'}
        ]
        edges = []

        positions = _calculate_force_directed_positions(nodes, edges)

        assert len(positions) == 3
        position_values = list(positions.values())

        # All positions should be different
        assert len(set(position_values)) == 3

    def test_connected_nodes_influence_positions(self):
        """Test that edges influence node positions."""
        nodes = [
            {'id': 'node1', 'name': 'test1'},
            {'id': 'node2', 'name': 'test2'}
        ]
        edges = [{'source': 'node1', 'target': 'node2', 'type': 'test'}]

        positions = _calculate_force_directed_positions(nodes, edges)

        assert len(positions) == 2
        assert 'node1' in positions
        assert 'node2' in positions


class TestGenerateGraphDownloadData:
    """Test suite for generate_graph_download_data function."""

    def test_generates_download_data(self):
        """Test that download data is generated properly."""
        # Create a simple figure
        fig = go.Figure(data=go.Scatter(x=[1, 2, 3], y=[4, 5, 6]))
        fig.update_layout(title="Test Graph")

        download_data = generate_graph_download_data(fig)

        assert isinstance(download_data, dict)
        assert 'html' in download_data
        assert 'json' in download_data
        assert 'png_available' in download_data
        assert 'svg_available' in download_data

        # HTML and JSON should be strings
        assert isinstance(download_data['html'], str)
        assert isinstance(download_data['json'], str)

        # Availability flags should be boolean
        assert isinstance(download_data['png_available'], bool)
        assert isinstance(download_data['svg_available'], bool)

    def test_html_contains_plotly_content(self):
        """Test that HTML download contains Plotly content."""
        fig = go.Figure(data=go.Scatter(x=[1, 2], y=[3, 4]))
        fig.update_layout(title="Test Graph")

        download_data = generate_graph_download_data(fig)
        html_content = download_data['html']

        assert "Test Graph" in html_content
        assert "plotly" in html_content.lower()

    def test_json_is_valid_plotly_json(self):
        """Test that JSON download is valid Plotly JSON."""
        import json

        fig = go.Figure(data=go.Scatter(x=[1, 2], y=[3, 4]))
        fig.update_layout(title="Test Graph")

        download_data = generate_graph_download_data(fig)
        json_content = download_data['json']

        # Should be valid JSON
        parsed_json = json.loads(json_content)
        assert isinstance(parsed_json, dict)

        # Should have Plotly structure
        assert 'data' in parsed_json
        assert 'layout' in parsed_json
