"""
Integration test for end-to-end graph visualization workflow.
"""

import pytest
from recipe_board.core.state import RecipeSessionState, ParsingState
from recipe_board.core.recipe import Ingredient, Equipment, Action
from recipe_board.agents.graph_tools import create_dependency_graph
import plotly.graph_objects as go


class TestGraphIntegration:
    """Integration tests for graph visualization workflow."""

    def test_complete_recipe_to_graph_workflow(self):
        """Test complete workflow from recipe state to dependency graph."""
        # Create a realistic recipe state
        state = RecipeSessionState()
        state.raw_text = "Mix flour and salt in a large bowl using a whisk. Bake in preheated oven."
        state.parsing_state = ParsingState.COMPLETED

        # Add ingredients
        flour = Ingredient(
            name="flour",
            amount=2.0,
            unit="cups",
            modifiers=["all-purpose"],
            raw_text="2 cups all-purpose flour"
        )
        salt = Ingredient(
            name="salt",
            amount=1.0,
            unit="tsp",
            modifiers=[],
            raw_text="1 tsp salt"
        )
        state.ingredients = [flour, salt]

        # Add equipment
        bowl = Equipment(name="mixing bowl", required=True, modifiers="large")
        whisk = Equipment(name="whisk", required=True, modifiers=None)
        oven = Equipment(name="oven", required=True, modifiers="preheated")
        state.equipment = [bowl, whisk, oven]

        # Add actions linking everything together
        mix_action = Action(
            name="mix",
            ingredient_ids=[flour.id, salt.id],
            equipment_id=bowl.id
        )
        whisk_action = Action(
            name="whisk",
            ingredient_ids=[flour.id, salt.id],
            equipment_id=whisk.id
        )
        bake_action = Action(
            name="bake",
            ingredient_ids=[flour.id],  # Assuming mixed flour goes to baking
            equipment_id=oven.id
        )
        state.actions = [mix_action, whisk_action, bake_action]

        # Generate graph
        fig = create_dependency_graph(state)

        # Verify graph structure
        assert isinstance(fig, go.Figure)
        assert len(fig.data) > 0  # Should have traces

        # Verify we have different node types
        node_traces = [trace for trace in fig.data if hasattr(trace, 'name') and trace.name]
        trace_names = [trace.name for trace in node_traces]

        # Should have ingredients, actions, and equipment traces
        expected_types = ['Ingredients', 'Actions', 'Equipment']
        found_types = [name for name in expected_types if name in trace_names]
        assert len(found_types) >= 2  # At least 2 of the 3 types should be present

        # Verify title
        assert "Recipe Dependency Graph" in fig.layout.title.text

    def test_minimal_recipe_graph(self):
        """Test graph creation with minimal recipe data."""
        state = RecipeSessionState()

        # Single ingredient, equipment, action
        ingredient = Ingredient(name="egg", amount=1, unit="piece", modifiers=[], raw_text="1 egg")
        equipment = Equipment(name="pan", required=True, modifiers=None)
        action = Action(name="crack", ingredient_ids=[ingredient.id], equipment_id=equipment.id)

        state.ingredients = [ingredient]
        state.equipment = [equipment]
        state.actions = [action]

        fig = create_dependency_graph(state)

        assert isinstance(fig, go.Figure)
        assert len(fig.data) > 0

        # Should have at least one edge connecting nodes
        edge_traces = [trace for trace in fig.data if trace.mode == 'lines']
        assert len(edge_traces) >= 1

    def test_complex_recipe_graph(self):
        """Test graph creation with complex recipe having multiple connections."""
        state = RecipeSessionState()

        # Multiple ingredients
        ingredients = [
            Ingredient(name="flour", amount=2, unit="cups", modifiers=[], raw_text="2 cups flour"),
            Ingredient(name="sugar", amount=1, unit="cup", modifiers=[], raw_text="1 cup sugar"),
            Ingredient(name="eggs", amount=3, unit="pieces", modifiers=[], raw_text="3 eggs"),
            Ingredient(name="butter", amount=0.5, unit="cup", modifiers=["melted"], raw_text="1/2 cup melted butter")
        ]

        # Multiple equipment pieces
        equipment = [
            Equipment(name="mixing bowl", required=True, modifiers="large"),
            Equipment(name="whisk", required=True, modifiers=None),
            Equipment(name="baking pan", required=True, modifiers="9x13 inch"),
            Equipment(name="oven", required=True, modifiers="preheated to 350°F")
        ]

        # Multiple actions with various connections
        actions = [
            Action(name="mix", ingredient_ids=[ingredients[0].id, ingredients[1].id], equipment_id=equipment[0].id),
            Action(name="whisk", ingredient_ids=[ingredients[2].id], equipment_id=equipment[1].id),
            Action(name="combine", ingredient_ids=[ingredients[0].id, ingredients[2].id, ingredients[3].id], equipment_id=equipment[0].id),
            Action(name="bake", ingredient_ids=[ingredients[0].id], equipment_id=equipment[3].id)
        ]

        state.ingredients = ingredients
        state.equipment = equipment
        state.actions = actions

        fig = create_dependency_graph(state)

        assert isinstance(fig, go.Figure)

        # Should have multiple traces for different node types
        traces_with_names = [trace for trace in fig.data if hasattr(trace, 'name') and trace.name]
        assert len(traces_with_names) >= 3  # Should have ingredients, actions, equipment

        # Verify we have edge connections
        edge_traces = [trace for trace in fig.data if hasattr(trace, 'mode') and trace.mode == 'lines']
        assert len(edge_traces) >= 1

        # Complex recipe should have many data points
        total_data_points = sum(len(trace.x) if hasattr(trace, 'x') and trace.x else 0 for trace in fig.data)
        assert total_data_points > 10  # Should have many nodes and edges

    def test_empty_state_graceful_handling(self):
        """Test that empty state is handled gracefully."""
        state = RecipeSessionState()
        # No ingredients, equipment, or actions

        fig = create_dependency_graph(state)

        assert isinstance(fig, go.Figure)
        # Should have annotation explaining no actions found
        assert len(fig.layout.annotations) > 0
        assert "No actions found" in fig.layout.annotations[0].text
