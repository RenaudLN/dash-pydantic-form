var dag = (window.dashAgGridComponentFunctions =
  window.dashAgGridComponentFunctions || {});

var dagfuncs = (window.dashAgGridFunctions = window.dashAgGridFunctions || {});

dag.PydfDeleteButton = (props) => {
  const onClick = () => {
    props.api.applyTransaction({ remove: [props.node.data], async: false });
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
    const inp = eGridCell.querySelector('.mantine-Select-input')
    inp.tabIndex = "1";
    inp.focus();
    colDef.suppressKeyboardEvent = (p) => {
      return p.editing;
    };
    const handleEscape = (e) => {
      if (e.code === "Escape") {
        stopEditing();
      }
    };
    document.addEventListener("keydown", handleEscape);
    return () => {
      document.removeEventListener("keydown", handleEscape);
    }
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
  const componentProps = (colDef.cellEditorParams || {});

  React.useEffect(() => {
    const inp = colDef.cellEditorPopup
    ? eGridCell.closest('div[class^="ag-theme-alpine"]').querySelector('.ag-popup-editor .mantine-DatePickerInput-input')
    : eGridCell.querySelector('.mantine-DatePickerInput-input');

    inp.click()

    const handleEscape = (e) => {
      if (e.code === "Escape") {
        props.stopEditing();
      }
    };
    document.addEventListener("keydown", handleEscape);
    return () => {
      document.removeEventListener("keydown", handleEscape);
    }
  }, []);

  componentProps.setProps = (newProps) => {
    if (typeof newProps.value === 'undefined') return
    delete colDef.suppressKeyboardEvent;
    node.setDataValue(column.colId, newProps.value || value);
    setValue(value)
    setTimeout(() => stopEditing(), 1);
  };


  return React.createElement(
    window.dash_mantine_components.DatePicker,
    {
      ...componentProps,
      value,
      returnFocus: true,
    }
  );
});


dagfuncs.selectRequiredCell = (params) => (
  params.colDef.cellEditorParams?.options || []
).map(o => o.value).includes(params.value) ? "" : "required_cell"



window.dash_clientside = window.dash_clientside || {}
dash_clientside.pydf = {
  getValues: () => {
    const inputs = dash_clientside.callback_context.inputs_list[0].concat(dash_clientside.callback_context.inputs_list[1])
    const formData = inputs.reduce((acc, val) => {
        const key = `${val.id.parent}:${val.id.field}`.replace(/^:/, "")
        const parts = key.split(":")
        let pointer = acc
        parts.forEach((part, i) => {
            if (i === parts.length - 1) {
                pointer[part] = val.value
            } else {
                const prt = /^\d+$/.test(part) ? Number(part) : part
                if (!pointer[prt]) {
                    pointer[prt] = /^\d+$/.test(parts[i + 1]) ? [] : {}
                }
                pointer = pointer[prt]
            }
        })
        return acc
    }, {})
    return formData
  }
}
