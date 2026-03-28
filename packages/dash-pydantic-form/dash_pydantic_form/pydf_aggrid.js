var dag = (window.dashAgGridComponentFunctions =
  window.dashAgGridComponentFunctions || {});

var dagfuncs = (window.dashAgGridFunctions = window.dashAgGridFunctions || {});

const {useRef, createElement, useEffect, useCallback, forwardRef, useMemo} = React

dag.PydfDeleteButton = (props) => {
  const onClick = () => {
    props.api.applyTransactionAsync({ remove: [props.node.data] });
  };
  return React.createElement(
    window.dash_mantine_components.ActionIcon,
    { onClick, color: "gray", variant: "subtle" },
    React.createElement(window.dash_iconify.DashIconify, {
      icon: "carbon:close",
      height: 16,
    })
  );
};

dag.PydfCheckbox = (props) => {
  const { setData, data } = props;
  const onClick = () => {
    if (!("checked" in event.target)) {
      const checked = !event.target.children[0].checked;
      const colId = props.column.colId;
      props.node.setDataValue(colId, checked);
    }
  };
  const checkedHandler = () => {
    // update grid data
    const checked = event.target.checked;
    const colId = props.column.colId;
    props.node.setDataValue(colId, checked);
    // update cellRendererData prop so it can be used to trigger a callback
    setData(checked);
  };
  return React.createElement(
    "div",
    { onClick: onClick },
    React.createElement("input", {
      type: "checkbox",
      checked: props.value,
      onChange: checkedHandler,
      style: { cursor: "pointer" },
    })
  );
};

dag.PydfOptionsRenderer = (props) => {
  const { node, column, api } = props;

  const [options, setOptions] = React.useState(props.colDef.cellEditorParams.options);

  React.useEffect(() => {
    const onDataChanged = (e) => {
      if (e && e.rowIndex !== node.rowIndex) return;
      let newOptions = props.colDef.cellEditorParams.options;
      if (props.colDef.cellEditorParams.dynamicOptions) {
        try {
          const { namespace, function_name } = props.colDef.cellEditorParams.dynamicOptions;
          const optionsFunc = window.dash_clientside[namespace][function_name];
          newOptions = optionsFunc(newOptions, node.data, props.colDef.cellEditorParams);
          if (!newOptions.map(o => typeof o === "string" ? o : o.value).includes(node.data[column.colId])) {
            node.setDataValue(column.colId, null);
          }
        } catch (e) {
          console.error(e);
        }
      }
      setOptions(newOptions);
    };
    onDataChanged()

    api.addEventListener("cellValueChanged", onDataChanged);

    return () => {
      api.removeEventListener("cellValueChanged", onDataChanged);
    };
  }, [node, column, api]);

  const optionMapper = Object.fromEntries(options.map((option) => [option.value, option.label]));

  let label;
  if (Array.isArray(props.value)) {
    label = props.value.map((v) => optionMapper[v]).join(", ");
  } else {
    label = optionMapper[props.value];
  }

  return React.createElement("span", {}, label);
};


dagfuncs.selectRequiredCell = (params) => (
  params.colDef.cellEditorParams?.options || []
).map(o => o.value).includes(params.value) ? "" : "required_cell"

dagfuncs.PydfDateComparator = (filterDate, cellValue) => {
  if (cellValue == null) return -1;
  const cellDate = new Date(cellValue);
  if (filterDate.getTime() === cellDate.getTime()) {
    return 0;
  }
  if (cellDate < filterDate) {
    return -1;
  }
  if (cellDate > filterDate) {
    return 1;
  }
};

dagfuncs.tableKeyboardNavigation = (props) => {
  const context = props.api.gos ? props.api.gos.gridOptions.context : props.context
  if (!context.rowsEditable) return;
  if (
    props.column.userProvidedColDef?.cellRenderer === "PydfDeleteButton" &&
    ["Enter", "NumpadEnter", "Space"].includes(props.event.code)
  ) {
    props.api.applyTransactionAsync({ remove: [props.node.data] });
    return
  }
  if (!context.autoAddRows) return;
  const displayedColumns = props.api.getAllDisplayedColumns();
  if (
    props.event.code === "Tab" &&
    !props.event.shiftKey &&
    ["INPUT", "TEXTAREA", "SELECT"].includes(props.event.target.tagName) &&
    props.node.rowIndex === props.api.getDisplayedRowCount() - 1 &&
    props.column.colId === displayedColumns[displayedColumns.length - 1].colId
  ) {
    const columnDefs = props.api.getColumnDefs();
    const newRow = Object.fromEntries(
      columnDefs
        .filter((colDef) => !!colDef.field)
        .map((colDef) => [colDef.field, colDef.default_value]),
    );
    props.api.applyTransactionAsync({ add: [newRow] }, (transaction) => {
      const firstColumn = displayedColumns.find((col) => col.getColDef().editable !== false);
      if (firstColumn) {
        props.api.setFocusedCell(transaction.add[0].rowIndex, firstColumn.colId);
        props.api.startEditingCell({
          rowIndex: transaction.add[0].rowIndex,
          colKey: firstColumn.colId,
        });
      }
    });
  }
};

dagfuncs.AllFunctionalComponentEditors = forwardRef(({ value, ...params }, ref) => {
    let comp = params.colDef.cellEditorParams.component;
    const node = useRef(params.api.getRowNode(params.node.id));
    const newValue = useRef(value);
    const escaped = useRef(null);
    const editorRef = useRef(null);
    const unsuppressedKeys = comp.type == 'Select' ? ['Tab'] : ['Enter', 'Tab']

    if (params.colDef.cellEditorParams.dynamicOptions) {
      try {
        const { namespace, function_name } = params.colDef.cellEditorParams.dynamicOptions
        const optionsFunc = window.dash_clientside[namespace][function_name]
        comp = {
          ...comp, props: {
            ...comp.props, data: optionsFunc(params.colDef.cellEditorParams.options, node.current.data, params.colDef.cellEditorParams)
          }
        }
      } catch (e) {
        console.error(e)
      }
    }

    const handleStop = ({ event, ...params }) => {
        setTimeout(() => {
            if (!escaped.current) {
                node.current.setDataValue(params.column.colId, newValue.current);
            }
        }, 1);
    };

    if (params.colDef.cellEditorPopup) {
        comp['props']['style'] = { ...comp.props?.style, width: params.column.actualWidth - 2 };
    }

    const setProps = (propsToSet) => {
        if ('value' in propsToSet) {
            newValue.current = propsToSet.value;
        }
    };

    const handleKeyDown = ({ key, ...event }) => {
        if (key == "Escape") {
            escaped.current = true;
        }
    };

    useEffect(() => {
        params.api.addEventListener('cellEditingStopped', handleStop);
        document.addEventListener('keydown', handleKeyDown);
        params.colDef.suppressKeyboardEvent = (params) => params.editing && !unsuppressedKeys.includes(params.event.key);
        return () => {
            document.removeEventListener('keydown', handleKeyDown);
            delete params.colDef.suppressKeyboardEvent;
            params.api.removeEventListener('cellEditingStopped', handleStop);
        };
    }, []);

    useEffect(() => {
        if (editorRef.current) {
            if (editorRef.current.querySelector('button.mantine-Input-input')) {
                editorRef.current.querySelector('button.mantine-Input-input').click()
            } else if (editorRef.current.querySelector('input')) {
                editorRef.current.querySelector('input').focus();
            } else {
                editorRef.current.focus()
            }
        }
    }, [editorRef.current]);

    const el = useMemo(() =>
        createElement(
            'div',
            { ref: editorRef, tabIndex: 0 },
            createElement(window[comp.namespace][comp.type], { ...comp.props, setProps, value })
        ),
    [comp]);

    return el;
});
