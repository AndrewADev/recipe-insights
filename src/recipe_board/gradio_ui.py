import gradio as gr
from wasabi import msg

from recipe_board.agents.parsing_agent import (
    parse_dependencies,
)
from recipe_board.agents.graph_tools import (
    create_dependency_graph,
    generate_graph_download_data,
)
from recipe_board.agents.entity_workflow import parse_recipe
from recipe_board.core.state import RecipeSessionState, ParsingState

from recipe_board.core.sample_recipes import (
    load_sample_recipes,
    create_recipe_preview,
    get_sample_recipe_choices,
)
from recipe_board.ui.how_to_tab import create_how_to_tab


def create_parser_tab(session_state, main_tabs):
    # First declare insights_tab_button as None - will be created later
    insights_tab_button = None

    with gr.Tab(label="Recipe", id="parser_tab"):

        gr.Markdown("# Recipe Insights")
        gr.Markdown(
            "Select a sample recipe or paste your own recipe text and click 'Parse Recipe' to analyze ingredients and equipment."
        )

        # Load sample recipes
        sample_recipes = load_sample_recipes()
        recipe_choices = get_sample_recipe_choices()

        with gr.Row():
            with gr.Column(scale=1):
                # Sample recipe dropdown and preview
                with gr.Accordion(
                    "Sample Recipes", open=True, elem_id="samples-accordion"
                ) as samples_accordion:
                    sample_dropdown = gr.Dropdown(
                        choices=recipe_choices,
                        label="Choose a sample recipe",
                        value="",
                        interactive=True,
                    )

                    with gr.Row():
                        copy_button = gr.Button(
                            "Copy to Input", size="sm", visible=False
                        )

                    recipe_preview = gr.Textbox(
                        label="Preview",
                        lines=6,
                        max_lines=8,
                        interactive=False,
                        visible=False,
                    )

                recipe_input = gr.Textbox(
                    label="Recipe Text",
                    placeholder="Paste your recipe here or select from samples above...\n\nExample:\n## Ingredients\n- 2 cups flour\n- 1 large onion, diced\n- 500g ground beef...",
                    lines=15,
                    max_lines=25,
                )

                parse_button = gr.Button("Parse Recipe", variant="primary", size="lg")
                visualize_button = gr.Button(
                    "Get Insights",
                    variant="primary",
                    size="lg",
                    interactive=False,
                )

            with gr.Column(scale=1):
                # Combined results: Ingredients + Equipment + Basic Actions
                combined_results = gr.Markdown(
                    value="**Click 'Parse Recipe' to analyze your recipe and see ingredients, equipment, and basic actions here.**",
                    elem_classes=["results-display"],
                )

                # Separate action dependencies display
                actions_output = gr.Markdown(
                    value="**Action dependencies will appear here after dependency parsing...**",
                    elem_classes=["actions-display"],
                )

        def get_button_text(parsing_state):
            """Get button text based on current parsing state."""
            if parsing_state == ParsingState.INITIAL:
                return "Parse Recipe"
            elif parsing_state == ParsingState.PARSING_RECIPE:
                return "Parsing..."
            elif parsing_state == ParsingState.PARSING_DEPENDENCIES:
                return "Parsing Dependencies..."
            elif parsing_state == ParsingState.DEPENDENCIES_ERROR:
                return "Retry Parsing"
            elif parsing_state == ParsingState.COMPLETED:
                return "Parse Recipe"
            else:
                return "Parse Recipe"

        def get_insights_button_state(state):
            """Get insights button enabled state based on current state."""
            return (
                state.parsing_state == ParsingState.COMPLETED and len(state.actions) > 0
            )

        def combined_parse_function(recipe_text, state):
            """Combined parsing function that handles recipe parsing and auto-triggers dependency parsing."""

            # Handle different button states
            if state.parsing_state == ParsingState.DEPENDENCIES_ERROR:
                # Retry dependency parsing only
                yield from retry_dependency_parsing(state)
                return

            # Initial parsing or new recipe
            try:
                # Step 1: Show parsing state immediately
                state.clear()
                state.raw_text = recipe_text
                state.parsing_state = ParsingState.PARSING_RECIPE

                # Yield immediate button state update
                yield (
                    "**Parsing recipe...**",  # Show immediate feedback in markdown
                    "**Parsing dependencies...**",  # Placeholder for dependencies
                    state,
                    gr.update(value="Parsing...", interactive=False),
                    gr.update(interactive=False),
                    gr.update(
                        interactive=False
                    ),  # Insights tab button disabled during parsing
                )

                # Parse using state-based function
                updated_state = parse_recipe(recipe_text)
                updated_state.parsing_state = ParsingState.PARSING_RECIPE

                # Format output for display
                ingredients_display = updated_state.format_ingredients_for_display()
                equipment_display = updated_state.format_equipment_for_display()
                basic_actions_display = updated_state.format_basic_actions_for_display()

                # Create combined markdown for ingredients + equipment + basic actions
                combined_output = f"## Ingredients\n{ingredients_display}\n\n## Equipment\n{equipment_display}\n\n## Basic Actions\n{basic_actions_display}"

                # Check if recipe parsing was successful
                has_basic_data = updated_state.has_parsed_data()
                has_basic_actions = len(updated_state.basic_actions) > 0

                if not (has_basic_data and has_basic_actions):
                    # Recipe parsing failed
                    updated_state.parsing_state = ParsingState.INITIAL
                    yield (
                        combined_output,
                        "",  # Empty actions output
                        updated_state,
                        gr.update(
                            value=get_button_text(updated_state.parsing_state),
                            interactive=True,
                        ),
                        gr.update(interactive=False),  # Keep visualize disabled
                        gr.update(interactive=False),  # Keep insights button disabled
                    )
                    return

                # Step 2: Show dependency parsing state
                updated_state.parsing_state = ParsingState.PARSING_DEPENDENCIES
                yield (
                    combined_output,
                    "**Parsing dependencies...**",
                    updated_state,
                    gr.update(value="Parsing Dependencies...", interactive=False),
                    gr.update(interactive=False),
                    gr.update(
                        interactive=False
                    ),  # Insights button disabled during dependency parsing
                )

                try:
                    # Parse dependencies
                    final_state = parse_dependencies(updated_state)
                    final_state.parsing_state = ParsingState.COMPLETED

                    # Format actions for display
                    actions_display = final_state.format_actions_for_display()
                    has_actions = len(final_state.actions) > 0

                    # Add header to actions display
                    if actions_display.strip():
                        actions_display = f"## Action Dependencies\n{actions_display}"

                    yield (
                        combined_output,
                        actions_display,
                        final_state,
                        gr.update(
                            value=get_button_text(final_state.parsing_state),
                            interactive=True,
                        ),
                        gr.update(interactive=has_actions),
                        gr.update(
                            interactive=get_insights_button_state(final_state)
                        ),  # Use helper function
                    )

                except Exception as dep_error:
                    # Dependency parsing failed - set retry state
                    updated_state.parsing_state = ParsingState.DEPENDENCIES_ERROR
                    msg.fail(f"Error parsing dependencies: {dep_error}")

                    yield (
                        combined_output,
                        f"**Error parsing dependencies:** {str(dep_error)}",
                        updated_state,
                        gr.update(
                            value=get_button_text(updated_state.parsing_state),
                            interactive=True,
                        ),
                        gr.update(interactive=False),
                        gr.update(
                            interactive=False
                        ),  # Insights button disabled on dependency error
                    )

            except Exception as e:
                # Recipe parsing failed
                msg.fail(f"Error parsing recipe: {e}")
                state.parsing_state = ParsingState.INITIAL
                error_msg = f"**Error parsing recipe:** {str(e)}"
                yield (
                    error_msg,
                    "",  # Empty actions output
                    state,
                    gr.update(
                        value=get_button_text(state.parsing_state), interactive=True
                    ),
                    gr.update(interactive=False),
                    gr.update(
                        interactive=False
                    ),  # Insights button disabled on recipe parsing error
                )

        def retry_dependency_parsing(state):
            """Retry dependency parsing after an error."""
            try:
                state.parsing_state = ParsingState.PARSING_DEPENDENCIES

                # Show immediate feedback
                ingredients_display = state.format_ingredients_for_display()
                equipment_display = state.format_equipment_for_display()
                basic_actions_display = state.format_basic_actions_for_display()
                combined_output = f"## Ingredients\n{ingredients_display}\n\n## Equipment\n{equipment_display}\n\n## Basic Actions\n{basic_actions_display}"

                yield (
                    combined_output,
                    "**Retrying dependency parsing...**",
                    state,
                    gr.update(value="Parsing Dependencies...", interactive=False),
                    gr.update(interactive=False),
                    gr.update(
                        interactive=False
                    ),  # Insights button disabled during retry
                )

                # Parse dependencies
                updated_state = parse_dependencies(state)
                updated_state.parsing_state = ParsingState.COMPLETED

                # Format updated displays
                ingredients_display = updated_state.format_ingredients_for_display()
                equipment_display = updated_state.format_equipment_for_display()
                basic_actions_display = updated_state.format_basic_actions_for_display()
                combined_output = f"## Ingredients\n{ingredients_display}\n\n## Equipment\n{equipment_display}\n\n## Basic Actions\n{basic_actions_display}"
                actions_display = updated_state.format_actions_for_display()

                has_actions = len(updated_state.actions) > 0

                # Add header to actions display
                if actions_display.strip():
                    actions_display = f"## Action Dependencies\n{actions_display}"

                yield (
                    combined_output,
                    actions_display,
                    updated_state,
                    gr.update(
                        value=get_button_text(updated_state.parsing_state),
                        interactive=True,
                    ),
                    gr.update(interactive=has_actions),
                    gr.update(
                        interactive=get_insights_button_state(updated_state)
                    ),  # Use helper function
                )

            except Exception as e:
                # Still failing - keep retry state
                msg.fail(f"Error retrying dependency parsing: {e}")
                ingredients_display = state.format_ingredients_for_display()
                equipment_display = state.format_equipment_for_display()
                basic_actions_display = state.format_basic_actions_for_display()
                combined_output = f"## Ingredients\n{ingredients_display}\n\n## Equipment\n{equipment_display}\n\n## Basic Actions\n{basic_actions_display}"

                yield (
                    combined_output,
                    f"**Error retrying dependency parsing:** {str(e)}",
                    state,
                    gr.update(
                        value=get_button_text(state.parsing_state), interactive=True
                    ),
                    gr.update(interactive=False),
                    gr.update(
                        interactive=False
                    ),  # Insights button disabled on retry error
                )

        def handle_sample_selection(selected_recipe):
            """Handle sample recipe dropdown selection."""
            if not selected_recipe:
                return (
                    gr.update(visible=False),  # Hide preview
                    "",  # Clear preview text
                    gr.update(visible=False),  # Hide copy button
                )

            # Get the full recipe text
            recipe_text = sample_recipes.get(selected_recipe, "")
            preview_text = create_recipe_preview(recipe_text)

            return (
                gr.update(visible=True),  # Show preview
                preview_text,  # Set preview text
                gr.update(visible=True),  # Show copy button
            )

        def copy_sample_to_input(selected_recipe):
            """Copy the selected sample recipe to the input textbox and close accordion."""
            if not selected_recipe:
                return "", gr.update()  # No change to accordion

            recipe_text = sample_recipes.get(selected_recipe, "")
            return recipe_text, gr.update(open=False)  # Close accordion after copy

        # Event handlers for sample recipe functionality
        sample_dropdown.change(
            fn=handle_sample_selection,
            inputs=[sample_dropdown],
            outputs=[recipe_preview, recipe_preview, copy_button],
        )

        copy_button.click(
            fn=copy_sample_to_input,
            inputs=[sample_dropdown],
            outputs=[recipe_input, samples_accordion],
        )

        # Store reference for later event binding
        parse_outputs = [
            combined_results,
            actions_output,
            session_state,
            parse_button,
            visualize_button,
        ]

        def create_dependency_visualization(state):
            """Create and display dependency graph."""
            if not state.actions:
                return (
                    None,
                    gr.update(visible=False),
                    gr.update(visible=False),
                    gr.update(),  # No tab change if no actions
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
                    gr.update(),  # No tab change on error
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

    with gr.Tab(label="Insights", id="visualization_tab") as visualization_tab:
        gr.Markdown("## 🕸️ Recipe Dependency Graph")
        graph_plot = gr.Plot(label="Recipe Dependency Graph", value=None)

        # Get Insights button for direct access from this tab
        with gr.Row():
            with gr.Column(scale=1):
                pass  # Empty column for centering
            with gr.Column(scale=2):
                insights_tab_button = gr.Button(
                    "Get Insights",
                    variant="primary",
                    size="lg",
                    interactive=False,
                )
            with gr.Column(scale=1):
                pass  # Empty column for centering

        # Now that insights_tab_button is created, wire up the parse button
        parse_outputs.append(insights_tab_button)
        parse_button.click(
            fn=combined_parse_function,
            inputs=[recipe_input, session_state],
            outputs=parse_outputs,
        )

        with gr.Row():
            download_html_btn = gr.DownloadButton(
                "Download as HTML", visible=False, size="sm"
            )
            download_json_btn = gr.DownloadButton(
                "Download as JSON", visible=False, size="sm"
            )

        visualize_button.click(
            fn=create_dependency_visualization,
            inputs=[session_state],
            outputs=[graph_plot, download_html_btn, download_json_btn, main_tabs],
        )

        # Wire up the Insights tab button to the same function
        insights_tab_button.click(
            fn=create_dependency_visualization,
            inputs=[session_state],
            outputs=[graph_plot, download_html_btn, download_json_btn, main_tabs],
        )

        download_html_btn.click(
            fn=download_graph_html,
            inputs=[session_state],
            outputs=[download_html_btn],
        )

        download_json_btn.click(
            fn=download_graph_json,
            inputs=[session_state],
            outputs=[download_json_btn],
        )

        # Feedback components

    with gr.Accordion("Feedback", open=False, elem_id="feedback-accordion"):
        gr.Markdown(
            "_By submitting feedback, you agree to your prompt and parsed data will be stored for analysis._"
        )
        with gr.Row():
            helpful_btn = gr.Button("👍 Helpful", size="sm")
            not_helpful_btn = gr.Button("👎 Not Helpful", size="sm")

    feedback_status = gr.Textbox(label="", visible=False)

    def handle_feedback(
        feedback_type, state, parsed_output, basic_actions_output, actions_output
    ):
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
            "basic_actions_display": basic_actions_output,
            "actions_display": actions_output,
        }

        # Save to flagged directory with timestamp
        filename = (
            f"flagged/feedback_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        )
        with open(filename, "w") as f:
            json.dump(feedback_data, f, indent=2)

        msg.info(f"User feedback saved to {filename}: {feedback_type}")
        return gr.update(
            value=f"Thanks! Feedback recorded: {feedback_type}", visible=True
        )

    helpful_btn.click(
        fn=lambda state, combined_output, actions_output: handle_feedback(
            "helpful", state, combined_output, "", actions_output
        ),
        inputs=[session_state, combined_results, actions_output],
        outputs=[feedback_status],
    )
    not_helpful_btn.click(
        fn=lambda state, combined_output, actions_output: handle_feedback(
            "not_helpful",
            state,
            combined_output,
            "",
            actions_output,
        ),
        inputs=[session_state, combined_results, actions_output],
        outputs=[feedback_status],
    )

    # Return key components for the Get Started button and insights button
    return sample_dropdown, recipe_input, samples_accordion, insights_tab_button


def create_ui():
    """Create and configure the Gradio interface."""
    with gr.Blocks(
        title="Recipe Insights - AI Recipe Analyzer",
        css="""
        .gradio-container { scroll-behavior: smooth; }
        .scroll-to-top { animation: scroll-top 0.3s ease-out; }
        @keyframes scroll-top {
            from { transform: translateY(10px); opacity: 0; }
            to { transform: translateY(0); opacity: 1; }
        }
        #samples-accordion { --accordion-state: auto; }
        #feedback-accordion { --accordion-state: auto; }
        """,
    ) as demo:
        # Create session state at the Blocks level
        session_state = gr.State(RecipeSessionState())

        # Add scroll trigger for smooth top navigation
        scroll_trigger = gr.HTML(visible=False)

        with gr.Tabs() as main_tabs:
            # Create how-to tab first for better UX
            get_started_button = create_how_to_tab()
            # Create parser tab and get component references
            sample_dropdown, recipe_input, samples_accordion, insights_tab_button = (
                create_parser_tab(session_state, main_tabs)
            )

            # Set up Get Started button functionality after both tabs are created
            def handle_get_started():
                """Handle Get Started button click - switch to parser tab and provide visual cues."""
                return (
                    gr.update(selected="parser_tab"),  # Switch to parser tab
                    gr.update(
                        value="",
                        placeholder="👈 Try selecting a sample recipe first, or paste your own recipe here!",
                    ),  # Update recipe input with helpful hint
                    gr.update(),  # Don't force accordion state - let it be natural
                    gr.update(
                        value='<script>setTimeout(() => window.scrollTo({top: 0, behavior: "smooth"}), 100);</script>',
                        visible=False,
                    ),  # Trigger smooth scroll to top
                )

            # Connect the Get Started button to the handler
            get_started_button.click(
                fn=handle_get_started,
                outputs=[main_tabs, recipe_input, samples_accordion, scroll_trigger],
            )

    return demo


def launch_ui(share=False, server_port=7860):
    """Launch the Gradio interface."""
    demo = create_ui()
    demo.launch(share=share, server_port=server_port)


if __name__ == "__main__":
    launch_ui()
