"""Fixed schemas for invented demonstration data."""
SCHEMAS = {
    'inventory': {
        'title': 'Synthetic inventory', 'id_column': 'sku', 'numeric_column': 'quantity',
        'category_column': 'status', 'minimum': 0, 'maximum': None,
        'categories': ['active', 'archived'],
    },
    'shipments': {
        'title': 'Synthetic shipment events', 'id_column': 'shipment_id', 'numeric_column': 'weight_kg',
        'category_column': 'status', 'minimum': 1, 'maximum': 1000,
        'categories': ['pending', 'in_transit', 'delivered'],
    },
    'equipment': {
        'title': 'Synthetic equipment records', 'id_column': 'asset_id', 'numeric_column': 'service_hours',
        'category_column': 'condition', 'minimum': 0, 'maximum': 100000,
        'categories': ['operational', 'maintenance', 'retired'],
    },
}


def dataset_info(dataset_id):
    return {'id': dataset_id, 'title': SCHEMAS[dataset_id]['title'],
            'dataset_version': f'{dataset_id}-v2'}
