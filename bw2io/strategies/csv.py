import warnings


def csv_restore_tuples(data):
    """
    Convert tuple-like strings to actual tuples.

    Parameters
    ----------
    data : list of dict
        A list of datasets.

    Returns
    -------
    list of dict
        A list of datasets with tuples restored from string.

    Examples
    --------
    >>> data = [{'categories': 'category1::category2'}, {'exchanges': [{'categories': 'category3::category4', 'amount': '10.0'}]}]
    >>> csv_restore_tuples(data)
    [{'categories': ('category1', 'category2')}, {'exchanges': [{'categories': ('category3', 'category4'), 'amount': '10.0'}]}]

    """
    _ = lambda x: tuple(x.split("::")) if "::" in x else x

    for ds in data:
        for key, value in ds.items():
            if isinstance(value, str):
                ds[key] = _(value)
            if key == "categories" and isinstance(ds[key], str):
                ds[key] = (ds[key],)
        for exc in ds.get("exchanges", []):
            for key, value in exc.items():
                if isinstance(value, str):
                    exc[key] = _(value)
                if key == "categories" and isinstance(exc[key], str):
                    exc[key] = (exc[key],)
    return data


def csv_restore_booleans(data):
    """
    Convert boolean-like strings to booleans where possible.

    Parameters
    ----------
    data : list of dict
        A list of datasets.

    Returns
    -------
    list of dict
        A list of datasets with booleans restored.

    Examples
    --------
    >>> data = [{'categories': 'category1', 'is_animal': 'true'}, {'exchanges': [{'categories': 'category2', 'amount': '10.0', 'uncertainty type': 'undefined', 'is_biomass': 'False'}]}]
    >>> csv_restore_booleans(data)
    [{'categories': 'category1', 'is_animal': True}, {'exchanges': [{'categories': 'category2', 'amount': '10.0', 'uncertainty type': 'undefined', 'is_biomass': False}]}]
    """

    def _(x):
        if x.lower() == "true":
            return True
        elif x.lower() == "false":
            return False
        else:
            return x

    for ds in data:
        for key, value in ds.items():
            if isinstance(value, str):
                ds[key] = _(value)
        for exc in ds.get("exchanges", []):
            for key, value in exc.items():
                if isinstance(value, str):
                    exc[key] = _(value)
    return data


def csv_numerize(data):
    """
    Convert string values to float or int where possible

    Parameters
    ----------
    data : list of dict
        A list of datasets.

    Returns
    -------
    list of dict
        A list of datasets with string values converted to float or int where possible.

    Examples
    --------
    >>> data = [{'amount': '10.0'}, {'exchanges': [{'amount': '20', 'uncertainty type': 'undefined'}]}]
    >>> csv_numerize(data)
    [{'amount': 10.0}, {'exchanges': [{'amount': 20, 'uncertainty type': 'undefined'}]}]
    """

    def _(x):
        try:
            return float(x)
        except:
            return x

    for ds in data:
        for key, value in ds.items():
            if isinstance(value, str):
                ds[key] = _(value)
        for exc in ds.get("exchanges", []):
            for key, value in exc.items():
                if isinstance(value, str):
                    exc[key] = _(value)
    return data


def csv_drop_unknown(data):
    """
    Remove any keys whose values are `(Unknown)`.

    Parameters
    ----------
    data : list[dict]
        A list of dictionaries, where each dictionary represents a row of data.

    Returns
    -------
    list[dict]
        The updated list of dictionaries with `(Unknown)` values removed from the keys.

    Examples
    --------
    >>> data = [
            {"name": "John", "age": 30, "gender": "(Unknown)"},
            {"name": "Alice", "age": 25, "gender": "Female"},
            {"name": "Bob", "age": 40, "gender": "Male"}
        ]
    >>> csv_drop_unknown(data)
        [
            {"name": "Alice", "age": 25, "gender": "Female"},
            {"name": "Bob", "age": 40, "gender": "Male"}
        ]
    """
    _ = lambda x: None if x == "(Unknown)" else x

    data = [{k: v for k, v in ds.items() if v != "(Unknown)"} for ds in data]

    for ds in data:
        if "exchanges" in ds:
            ds["exchanges"] = [
                {k: v for k, v in exc.items() if v != "(Unknown)"}
                for exc in ds["exchanges"]
            ]

    return data


def csv_add_missing_exchanges_section(data):
    """
    Add an empty `exchanges` section to any dictionary in `data` that doesn't already have one.

    Parameters
    ----------
    data: list of dict
        A list of dictionaries, where each dictionary represents a row of data.

    Returns
    -------
    list[dict]
        The updated list of dictionaries with an empty `exchanges` section added to any dictionary that doesn't already have one.

    Examples
    --------
    >>> data = [
            {"name": "John", "age": 30},
            {"name": "Alice", "age": 25, "exchanges": []},
            {"name": "Bob", "age": 40, "exchanges": [{"name": "NYSE"}]}
        ]
    >>> csv_add_missing_exchanges_section(data)
        [
            {"name": "John", "age": 30, "exchanges": []},
            {"name": "Alice", "age": 25, "exchanges": []},
            {"name": "Bob", "age": 40, "exchanges": [{"name": "NYSE"}]}
        ]
    """
    for ds in data:
        if "exchanges" not in ds:
            ds["exchanges"] = []
    return data


_LOADER_MAP_TD = {
    # Full names as produced automatically by to_json()
    "bw_temporalis.TemporalDistribution": "TemporalDistribution",
    "bw_temporalis.FixedTD": "FixedTD",
    "bw_temporalis.FixedTimeOfYearTD": "FixedTimeOfYearTD",
    # Short names as a convenience for manually constructed JSON
    "TemporalDistribution": "TemporalDistribution",
    "FixedTD": "FixedTD",
    "FixedTimeOfYearTD": "FixedTimeOfYearTD",
}


def _get_temporalis_classes():
    """Import and return the three TD classes from bw_temporalis.

    Raises
    ------
    ImportError
        If bw_temporalis is not installed.
    """
    try:
        from bw_temporalis import FixedTD, FixedTimeOfYearTD, TemporalDistribution

        return {
            "TemporalDistribution": TemporalDistribution,
            "FixedTD": FixedTD,
            "FixedTimeOfYearTD": FixedTimeOfYearTD,
        }
    except ImportError:
        raise ImportError(
            "The `bw_temporalis` package is required to import spreadsheets that "
            "contain a `temporal_distribution` column. "
            "Install it with:  pip install bw_temporalis"
        )


def _deserialize_td(raw: str):
    """Deserialize a single JSON string into the appropriate TD object.

    Parameters
    ----------
    raw:
        The raw string value read from the spreadsheet cell, expected to be
        the JSON produced by ``TemporalDistribution.to_json()`` (or one of its
        subclasses)
        This JSON format is currently the only supported format for temporal
        distributions in spreadsheets.

    Returns
    -------
    TemporalDistribution | FixedTD | FixedTimeOfYearTD
        The reconstructed temporal distribution object.

    Raises
    ------
    ImportError
        If bw_temporalis is not installed.
    ValueError
        If the JSON is missing the ``__loader__`` key or names an unknown class.
    """
    import json

    try:
        data = json.loads(raw)
    except (json.JSONDecodeError, TypeError) as exc:
        raise ValueError(
            f"Could not parse `temporal_distribution` value as JSON: {raw!r}"
        ) from exc

    loader_key = data.get("__loader__")
    if loader_key is None:
        raise ValueError(
            "JSON in `temporal_distribution` column is missing the "
            f"`__loader__` key. Got keys: {list(data.keys())}"
        )

    class_name = _LOADER_MAP_TD.get(loader_key)
    if class_name is None:
        raise ValueError(
            f"Unknown `__loader__` value {loader_key!r} in `temporal_distribution` "
            f"column. Supported loaders: {list(_LOADER_MAP_TD.keys())}"
        )

    classes = _get_temporalis_classes()
    return classes[class_name].from_json(data)


def csv_restore_temporal_distributions(data: list[dict]) -> list[dict]:
    """Convert ``temporal_distribution`` JSON strings on exchanges into objects.

    This strategy scans every exchange in every dataset in *data*.  When it
    finds a ``temporal_distribution`` key whose value is a ``str`` it
    deserializes it into the appropriate ``bw_temporalis`` object
    (``TemporalDistribution``, ``FixedTD``, or ``FixedTimeOfYearTD``) using
    that class's ``from_json()`` classmethod.

    Although other formats are conceivable, the JSON format is currently the
    only supported format for temporal distributions in spreadsheets.

    The ``__loader__`` key embedded by ``to_json()`` is used to dispatch to
    the correct class, so all three subclasses are handled automatically.

    Parameters
    ----------
    data:
        A list of activity dicts, each optionally containing an ``exchanges``
        list.  This is the standard format used throughout bw2io strategies.

    Returns
    -------
    list[dict]
        The same list, mutated in-place, with ``temporal_distribution`` string
        values replaced by the corresponding TD objects.

    Raises
    ------
    ImportError
        If ``bw_temporalis`` is not installed and a ``temporal_distribution``
        field is encountered.
    ValueError
        If a ``temporal_distribution`` value cannot be parsed as JSON, is
        missing the ``__loader__`` key, or names an unknown loader class.
        Note: errors relating to malformed ``date``, ``amount``, or
        ``date_dtype`` values (e.g. mismatched array shapes, wrong dtype)
        are raised by ``bw_temporalis`` itself via its ``from_json()`` and
        ``__init__()`` methods, and will bubble up naturally with descriptive
        messages from that package.

    Examples
    --------
    The JSON strings below are what ``TemporalDistribution.to_json()`` and
    ``FixedTD.to_json()`` produce; you would normally put these in a single
    spreadsheet cell.

    >>> import json, numpy as np
    >>> from bw_temporalis import TemporalDistribution
    >>> td = TemporalDistribution(
    ...     date=np.array([-1, 0, 1], dtype="timedelta64[Y]"),
    ...     amount=np.array([0.25, 0.5, 0.25]),
    ... )
    >>> data = [
    ...     {
    ...         "name": "my activity",
    ...         "exchanges": [
    ...             {
    ...                 "name": "electricity",
    ...                 "amount": 3.5,
    ...                 "temporal_distribution": td.to_json(),
    ...             }
    ...         ],
    ...     }
    ... ]
    >>> result = csv_restore_temporal_distributions(data)
    >>> type(result[0]["exchanges"][0]["temporal_distribution"])
    <class 'bw_temporalis.temporal_distribution.TemporalDistribution'>
    """
    for ds in data:
        for exc in ds.get("exchanges", []):
            raw = exc.get("temporal_distribution")
            if isinstance(raw, str):
                exc["temporal_distribution"] = _deserialize_td(raw)
    return data
