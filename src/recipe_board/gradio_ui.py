import gradio as gr

from recipe_board.agents.recipe_parser import parse_recipe


def create_ui():
    """Create and configure the Gradio interface."""
    with gr.Blocks(title="Recipe Board - AI Recipe Analyzer") as demo:
        gr.Markdown("# Recipe Board")
        gr.Markdown(
            "Paste your recipe text on the left and click 'Parse Recipe' to analyze the ingredients."
        )

        with gr.Row():
            with gr.Column(scale=1):
                recipe_input = gr.Textbox(
                    label="Recipe Text",
                    placeholder="Paste your recipe here...\n\nExample:\n## Ingredients\n- 2 cups flour\n- 1 large onion, diced\n- 500g ground beef",
                    lines=20,
                    max_lines=30,
                )

                parse_button = gr.Button("Parse Recipe", variant="primary", size="lg")

            with gr.Column(scale=1):
                ingredients_table = gr.Dataframe(
                    label="Parsed Ingredients",
                    headers=["Amount", "Unit", "Name", "Modifiers", "Raw Text"],
                    datatype=["str", "str", "str", "str", "str"],
                    row_count=(5, "dynamic"),
                    col_count=(5, "fixed"),
                    interactive=False,
                )

        # Wire up the parsing function
        parse_button.click(
            fn=parse_recipe, inputs=[recipe_input], outputs=[ingredients_table]
        )

        # Example recipes section
        with gr.Accordion("Example Recipes", open=False):
            gr.Markdown(
                """
            Try pasting one of these example recipes:

            **Simple Recipe:**
            ```
            ## Ingredients
            - 2 cups all-purpose flour
            - 1 tsp salt
            - 1/2 cup olive oil
            - 1 large onion, diced
            ```

            **Complex Recipe:**
            ```
            ## Ingredients
            - 500g ground beef (80/20 lean)
            - 2 tbsp olive oil
            - 1 large onion, finely chopped
            - 3 cloves garlic, minced
            - 400g can crushed tomatoes
            - 1/2 cup red wine (optional)
            ```
            """
            )

    return demo


def launch_ui(share=False, server_port=7860):
    """Launch the Gradio interface."""
    demo = create_ui()
    demo.launch(share=share, server_port=server_port)


if __name__ == "__main__":
    launch_ui()
