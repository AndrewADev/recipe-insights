import gradio as gr
from wasabi import msg

from recipe_board.agents.models import (
    parse_recipe,
    parse_actions,
)
from recipe_board.agents.graph_tools import (
    create_dependency_graph,
    generate_graph_download_data,
)
from recipe_board.core.state import RecipeSessionState


def create_parser_tab(session_state):
    with gr.Tab(label="Parser"):

        gr.Markdown("# Recipe Board")
        gr.Markdown(
            "Paste your recipe text on the left and click 'Parse Recipe' to analyze ingredients and equipment."
        )

        with gr.Row():
            with gr.Column(scale=1):
                recipe_input = gr.Textbox(
                    label="Recipe Text",
                    placeholder="Paste your recipe here...\n\nExample:\n## Ingredients\n- 2 cups flour\n- 1 large onion, diced\n- 500g ground beef...",
                    lines=20,
                    max_lines=30,
                )

                parse_button = gr.Button("Parse Recipe", variant="primary", size="lg")
                parse_actions_button = gr.Button(
                    "Parse Actions", variant="secondary", size="lg", interactive=False
                )
                visualize_button = gr.Button(
                    "Visualize Dependencies",
                    variant="primary",
                    size="lg",
                    interactive=False,
                )

            with gr.Column(scale=1):
                with gr.Tabs() as results_tabs:
                    with gr.Tab(label="Parsing", id="parsing_tab") as parsing_tab:
                        parsed_output = gr.Textbox(
                            label="Parsed Results",
                            placeholder="Parsed ingredients and equipment will appear here...",
                            lines=10,
                            max_lines=15,
                        )

                        actions_output = gr.Textbox(
                            label="Parsed Actions",
                            placeholder="Parsed actions will appear here after ingredients and equipment are processed...",
                            lines=10,
                            max_lines=15,
                        )

                    with gr.Tab(
                        label="Visualization", id="visualization_tab"
                    ) as visualization_tab:
                        graph_plot = gr.Plot(
                            label="Recipe Dependency Graph", value=None
                        )

                        with gr.Row():
                            download_html_btn = gr.DownloadButton(
                                "Download as HTML", visible=False, size="sm"
                            )
                            download_json_btn = gr.DownloadButton(
                                "Download as JSON", visible=False, size="sm"
                            )

        def parse_recipe_and_enable_actions(recipe_text, state):
            """Parse recipe and return formatted results, updated state, and button state."""
            try:
                # Update state with new recipe text and parse
                state.clear()
                state.raw_text = recipe_text

                # Parse using new state-based function
                updated_state = parse_recipe(recipe_text)

                # Format output for display
                ingredients_display = updated_state.format_ingredients_for_display()
                equipment_display = updated_state.format_equipment_for_display()
                combined_output = f"## Ingredients\n{ingredients_display}\n\n## Equipment\n{equipment_display}"

                # Check if parsing was successful
                is_valid = updated_state.has_parsed_data()

                return combined_output, updated_state, gr.update(interactive=is_valid)

            except Exception as e:
                msg.fail(f"Error parsing recipe: {e}")
                error_msg = f"Error parsing recipe: {str(e)}"
                return error_msg, state, gr.update(interactive=False)

        def parse_actions_from_state(state):
            """Parse actions from recipe state."""
            if not state.has_parsed_data():
                return (
                    "Error: No ingredients or equipment found. Please parse recipe first.",
                    state,
                    gr.update(interactive=False),  # Keep visualize button disabled
                )

            try:
                # Parse actions using state-based function
                updated_state = parse_actions(state)

                # Format actions for display
                actions_display = updated_state.format_actions_for_display()

                # Enable visualize button if actions were found
                has_actions = len(updated_state.actions) > 0

                return (
                    actions_display,
                    updated_state,
                    gr.update(interactive=has_actions),
                )

            except ValueError as e:
                return (
                    f"Error parsing actions: {str(e)}",
                    state,
                    gr.update(interactive=False),
                )
            except Exception as e:
                msg.fail(f"Unexpected error in actions parsing: {e}")
                return (
                    f"Unexpected error occurred while parsing actions: {str(e)}",
                    state,
                    gr.update(interactive=False),
                )

        parse_button.click(
            fn=parse_recipe_and_enable_actions,
            inputs=[recipe_input, session_state],
            outputs=[parsed_output, session_state, parse_actions_button],
        )

        def create_dependency_visualization(state):
            """Create and display dependency graph."""
            if not state.actions:
                return (
                    None,
                    gr.update(visible=False),
                    gr.update(visible=False),
                    gr.update(selected="parsing_tab"),  # Stay on parsing tab
                )

            try:
                # Generate the graph
                fig = create_dependency_graph(state)

                # Generate download data
                download_data = generate_graph_download_data(fig)

                # Show download buttons if data is available
                html_visible = download_data.get("html") is not None
                json_visible = download_data.get("json") is not None

                return (
                    fig,
                    gr.update(visible=html_visible),
                    gr.update(visible=json_visible),
                    gr.update(
                        selected="visualization_tab"
                    ),  # Switch to visualization tab
                )

            except Exception as e:
                msg.fail(f"Error creating dependency graph: {e}")
                return (
                    None,
                    gr.update(visible=False),
                    gr.update(visible=False),
                    gr.update(selected="parsing_tab"),
                )

        def download_graph_html(state):
            """Generate HTML file for download."""
            if not state.actions:
                return None
            try:
                fig = create_dependency_graph(state)
                import tempfile
                import os

                # Create temporary file
                with tempfile.NamedTemporaryFile(
                    mode="w", suffix=".html", delete=False
                ) as f:
                    f.write(fig.to_html(include_plotlyjs=True))
                    return f.name
            except Exception as e:
                msg.warn(f"Error generating HTML download: {e}")
                return None

        def download_graph_json(state):
            """Generate JSON file for download."""
            if not state.actions:
                return None
            try:
                fig = create_dependency_graph(state)
                import tempfile
                import os

                # Create temporary file
                with tempfile.NamedTemporaryFile(
                    mode="w", suffix=".json", delete=False
                ) as f:
                    f.write(fig.to_json())
                    return f.name
            except Exception as e:
                msg.warn(f"Error generating JSON download: {e}")
                return None

        parse_actions_button.click(
            fn=parse_actions_from_state,
            inputs=[session_state],
            outputs=[actions_output, session_state, visualize_button],
        )

        visualize_button.click(
            fn=create_dependency_visualization,
            inputs=[session_state],
            outputs=[graph_plot, download_html_btn, download_json_btn, results_tabs],
        )

        download_html_btn.click(
            fn=download_graph_html,
            inputs=[session_state],
            outputs=None,
        )

        download_json_btn.click(
            fn=download_graph_json,
            inputs=[session_state],
            outputs=None,
        )

        # Feedback components

        with gr.Group():
            gr.Markdown("### Feedback")
            gr.Markdown(
                "_By submitting feedback, you agree to your prompt and parsed data will be stored for analysis._"
            )
            with gr.Row():
                helpful_btn = gr.Button("👍 Helpful", size="sm")
                not_helpful_btn = gr.Button("👎 Not Helpful", size="sm")

        feedback_status = gr.Textbox(label="", visible=False)

        def handle_feedback(feedback_type, state, parsed_output, actions_output):
            import json
            import datetime
            import os

            # Ensure flagged directory exists
            os.makedirs("flagged", exist_ok=True)

            feedback_data = {
                "timestamp": datetime.datetime.now().isoformat(),
                "feedback": feedback_type,
                "input": state.raw_text,
                "state": state.to_dict(),
                "output_display": parsed_output,
                "actions_display": actions_output,
            }

            # Save to flagged directory with timestamp
            filename = f"flagged/feedback_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            with open(filename, "w") as f:
                json.dump(feedback_data, f, indent=2)

            msg.info(f"User feedback saved to {filename}: {feedback_type}")
            return gr.update(
                value=f"Thanks! Feedback recorded: {feedback_type}", visible=True
            )

        helpful_btn.click(
            fn=lambda state, parsed_output, actions_output: handle_feedback(
                "helpful", state, parsed_output, actions_output
            ),
            inputs=[session_state, parsed_output, actions_output],
            outputs=[feedback_status],
        )
        not_helpful_btn.click(
            fn=lambda state, parsed_output, actions_output: handle_feedback(
                "not_helpful", state, parsed_output, actions_output
            ),
            inputs=[session_state, parsed_output, actions_output],
            outputs=[feedback_status],
        )


def create_ui():
    """Create and configure the Gradio interface."""
    with gr.Blocks(title="Recipe Board - AI Recipe Analyzer") as demo:
        # Create session state at the Blocks level
        session_state = gr.State(RecipeSessionState())
        create_parser_tab(session_state)

    return demo


def launch_ui(share=False, server_port=7860):
    """Launch the Gradio interface."""
    demo = create_ui()
    demo.launch(share=share, server_port=server_port)


if __name__ == "__main__":
    launch_ui()
