var dag = (window.dashAgGridComponentFunctions =
  window.dashAgGridComponentFunctions || {});

var dagfuncs = (window.dashAgGridFunctions = window.dashAgGridFunctions || {});

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
  const label =
    props.colDef.cellEditorParams.options.find((p) => p.value === props.value)
      ?.label || "";
  return React.createElement("span", {}, label);
};

dagfuncs.PydfDropdown = React.forwardRef((props, ref) => {
  const { value: initialValue, options, colDef, eGridCell, node, column, stopEditing } = props;
  const [value, setValue] = React.useState(initialValue);
  const componentProps = (colDef.cellEditorParams || {});

  React.useEffect(() => {
    const inp = colDef.cellEditorPopup
    ? eGridCell.closest('div[class^="ag-theme-alpine"]').querySelector('.ag-popup-editor .mantine-Select-input')
    : eGridCell.querySelector('.mantine-Select-input');
    inp.tabIndex = "1";
    inp.focus();
    colDef.suppressKeyboardEvent = (p) => {
      return p.editing;
    };
  }, [])

  const setProps = (newProps) => {
    if (typeof newProps.value === 'undefined') return
    delete colDef.suppressKeyboardEvent;
    node.setDataValue(column.colId, newProps.value);
    setValue(value)
    setTimeout(() => stopEditing(), 1);
  }

  return React.createElement(window.dash_mantine_components.Select, {
      setProps,
      ref,
      data: options,
      value: value,
      clearable: componentProps.clearable || true,
      searchable: componentProps.searchable || true,
      selectFirstOptionOnChange: componentProps.selectFirstOptionOnChange || true,
      allowDeselect: componentProps.allowDeselect || true,
      style: { width: column.actualWidth },
  })
})

dagfuncs.PydfDatePicker = React.forwardRef((props, ref) => {
  const { value: initialValue, colDef, eGridCell, node, column, stopEditing } = props;
  const [value, setValue] = React.useState(initialValue);
  const componentProps = {...colDef.cellEditorParams};

  React.useEffect(() => {
    const inp = colDef.cellEditorPopup
    ? eGridCell.closest('div[class^="ag-theme-alpine"]').querySelector('.ag-popup-editor .mantine-DateInput-input')
    : eGridCell.querySelector('.mantine-DateInput-input');
    inp.focus()
  }, []);

  componentProps.setProps = (newProps) => {
    if (typeof newProps.value === 'undefined') return
    delete colDef.suppressKeyboardEvent;
    node.setDataValue(column.colId, newProps.value);
    setValue(newProps.value)
  };


  return React.createElement(
    window.dash_mantine_components.DateInput,
    {
      ...componentProps,
      value,
      returnFocus: true,
    }
  );
});

dagfuncs.PydfDatetimePicker = React.forwardRef((props, ref) => {
  const { value: initialValue, colDef, eGridCell, node, column, stopEditing } = props;
  const [value, setValue] = React.useState(initialValue);
  const componentProps = {...colDef.cellEditorParams};

  React.useEffect(() => {
    const inp = colDef.cellEditorPopup
    ? eGridCell.closest('div[class^="ag-theme-alpine"]').querySelector('.ag-popup-editor .mantine-DateTimePicker-input')
    : eGridCell.querySelector('.mantine-DateTimePicker-input');
    inp.click();
    colDef.suppressKeyboardEvent = (p) => {
      return p.editing;
    };
  }, []);

  componentProps.setProps = (newProps) => {
    if (typeof newProps.value === 'undefined') return
    delete colDef.suppressKeyboardEvent;
    node.setDataValue(column.colId, newProps.value);
    setValue(newProps.value)
  };


  return React.createElement(
    window.dash_mantine_components.DateTimePicker,
    {
      ...componentProps,
      value,
      popoverProps: {withinPortal: false},
      style: { width: column.actualWidth },
    }
  );
});

dagfuncs.PydfTimePicker = React.forwardRef((props, ref) => {
  const { value: initialValue, colDef, eGridCell, node, column, stopEditing } = props;
  const [value, setValue] = React.useState(initialValue);
  const componentProps = {...colDef.cellEditorParams};

  React.useEffect(() => {
    const inp = colDef.cellEditorPopup
    ? eGridCell.closest('div[class^="ag-theme-alpine"]').querySelector('.ag-popup-editor .mantine-TimeInput-input')
    : eGridCell.querySelector('.mantine-TimeInput-input');
    inp.focus();
    colDef.suppressKeyboardEvent = (p) => {
      return p.editing;
    };
  }, []);

  componentProps.setProps = (newProps) => {
    if (typeof newProps.value === 'undefined') return
    delete colDef.suppressKeyboardEvent;
    node.setDataValue(column.colId, newProps.value);
    setValue(newProps.value)
  };


  return React.createElement(
    window.dash_mantine_components.TimeInput,
    {
      ...componentProps,
      value,
    }
  );
});


dagfuncs.selectRequiredCell = (params) => (
  params.colDef.cellEditorParams?.options || []
).map(o => o.value).includes(params.value) ? "" : "required_cell"

dagfuncs.PydfDateComparator = (filterLocalDateAtMidnight, cellValue) => {
  const dateAsString = cellValue;
  if (dateAsString == null) return -1;
  const dateParts = dateAsString.split('-');
  const cellDate = new Date(Number(dateParts[0]), Number(dateParts[1]) - 1, Number(dateParts[2]));
  if (filterLocalDateAtMidnight.getTime() === cellDate.getTime()) {
    return 0;
  }
  if (cellDate < filterLocalDateAtMidnight) {
    return -1;
  }
  if (cellDate > filterLocalDateAtMidnight) {
    return 1;
  }
};
