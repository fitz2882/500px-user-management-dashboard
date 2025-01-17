from .callbacks import (
    initialize_and_reset_data,
    update_selected_users,
    update_page_number,
    update_table,
    update_total_records_display,
    export_selected_rows,
    reset_filters,
    reload_data
)

def register_callbacks(app):
    initialize_and_reset_data(app)
    update_page_number(app)
    update_selected_users(app)
    update_table(app)
    update_total_records_display(app)
    export_selected_rows(app)
    reset_filters(app)
    reload_data(app)
