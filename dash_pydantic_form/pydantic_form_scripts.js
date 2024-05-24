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
    node.setDataValue(column.colId, newProps.value || value);
    setValue(value)
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


dagfuncs.selectRequiredCell = (params) => (
  params.colDef.cellEditorParams?.options || []
).map(o => o.value).includes(params.value) ? "" : "required_cell"


function waitForElem(id) {
  return new Promise(resolve => {
      if (document.getElementById(id)) {
          return resolve(document.getElementById(id));
      }

      const observer = new MutationObserver(mutations => {
          if (document.getElementById(id)) {
              observer.disconnect();
              resolve(document.getElementById(id));
          }
      });

      // If you get "parameter 1 is not of type 'Node'" error, see https://stackoverflow.com/a/77855838/492336
      observer.observe(document.body, {
          childList: true,
          subtree: true
      });
  });
}


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
  },
  updateFieldVisibility: (value, checked) => {

    const checkVisibility = (value, operator, expectedValue) => {
        switch (operator) {
            case "==":
                return value == expectedValue
            case "!=":
                return value != expectedValue
            case "in":
                return expectedValue.includes(value)
            case "not in":
                return !expectedValue.includes(value)
            case "array_contains":
                return value.includes(expectedValue)
            case "array_contains_any":
                return value.some(v => expectedValue.includes(v))
            default:
                return true
        }
    }

    const newStyles = []
    let actualValue
    if (value.length > 0) {
        actualValue = value[0]
    } else {
        actualValue = checked[0]
    }
    // Iterate through each visibility wrapper and check its dependent field value
    // to update its display property
    dash_clientside.callback_context.states_list[0].forEach(state => {
        let [_f, operator, expectedValue] = state.id.meta.split("|")
        expectedValue = JSON.parse(expectedValue)
        newStyles.push({
            ...state.value,
            display: checkVisibility(actualValue, operator, expectedValue) ? null : "none",
        })
    })

    return newStyles
  },
  sync: x => x,
  syncTrue: x => !!x,
  syncFalse: x => !x,
  updateModalTitle: (val) => {
    return val != null ? Array(2).fill(String(val)) : Array(2).fill(dash_clientside.no_update)
  },
  updateAccordionTitle: (val) => {
    return val != null ? String(val) : dash_clientside.no_update
  },
  syncTableJson: (rowData, virtualRowData) => {
    let val = rowData
    if (
        dash_clientside.callback_context.triggered.map(
            x => x.prop_id.split(".").slice(-1)[0]
        )
        .includes("virtualRowData")
    ) {
        val = virtualRowData
    }
    return val.filter(row => Object.values(row).some(x => x != null))
  },
  stepsClickListener: (id) => {
    const strId = JSON.stringify(id, Object.keys(id).sort())
    waitForElem(strId).then((elem) => {
      const steps = elem.children[0].children
      for (let i = 0; i < steps.length; i++) {
          const child = steps[i]
          child.addEventListener("click", event => {
              dash_clientside.set_props(id, {active: i})
          })
      }
    })

    return dash_clientside.no_update
  },
  stepsDisable: (active, nSteps) => [active === 0, active === nSteps],
  stepsPreviousNext: (_t1, _t2, active, nSteps) => {
    const trigger = dash_clientside.callback_context.triggered
    if (!trigger || trigger.length === 0) return dash_clientside.no_update
    const trigger_id = JSON.parse(trigger[0].prop_id.split(".")[0])
    if (trigger_id.part.includes("next")) return Math.min(active + 1, nSteps)
    if (trigger_id.part.includes("previous")) return Math.max(0, active - 1)
    return dash_clientside.no_update
  },
  listenToSubmit: (id, enterSubmits) => {
    const el = document.getElementById(
      JSON.stringify(id, Object.keys(id).sort())
    )
    if (el && enterSubmits) {
      el.addEventListener("keypress", event => {
          if (event.key === "Enter" && event.target.tagName === "INPUT") {
              event.preventDefault()
              dash_clientside.set_props(id, {"data-submit": 1})
          }
      })
    }
    return dash_clientside.no_update
  },
  displayErrors: (errors, ids) => {
    if (!errors) return Array(ids.length).fill(null)

    return ids.map(id => {
      const fullPath = id.parent ? `${id.parent}:${id.field}` : id.field
      return errors[fullPath]
    })
  }
}
