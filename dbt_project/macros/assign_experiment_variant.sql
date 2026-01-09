{% macro assign_experiment_variant(user_id_column, experiment_config) %}
    CASE
        WHEN abs(hash({{ user_id_column }})) % 100 < ({{ experiment_config.control_allocation }} * 100)::INT
            THEN 'control'
        ELSE 'variant_b'
    END
{% endmacro %}
