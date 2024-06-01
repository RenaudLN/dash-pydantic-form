window.dash_clientside = window.dash_clientside || {}

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
  },
  addToList: (trigger, current, template) => {
    if (trigger == null) return dash_clientside.no_update
    const path = getFullpath(
      dash_clientside.callback_context.triggered_id.parent,
      dash_clientside.callback_context.triggered_id.field,
    )
    const templateCopy = JSON.parse(template)
    return [...current, updateModelListIds(templateCopy, path, current.length)]
  },
  deleteFromList: (trigger, current) => {
    // return dash_clientside.no_update
    if (trigger.every(t => t == null)) return dash_clientside.no_update
    const idx = dash_clientside.callback_context.triggered_id.meta
    const path = getFullpath(
      dash_clientside.callback_context.triggered_id.parent,
      dash_clientside.callback_context.triggered_id.field,
    )
    const newChildren = current.filter((_, i) => i !== idx)
    return newChildren.map((child, i) => updateModelListIds(child, path, i))
  }
}

// Return a : separated string of the args
const getFullpath = (...args) => {
  return args.filter(x => x != null && x !== "").join(":")
}

const updateModelListIds = (child, path, newIdx) => {
  if (typeof child !== 'object' || child === null) return child
  Object.entries(child).forEach(([key, val]) => {
    if (key === "id" && typeof val === "object" && val.parent != null) {
      val.parent = val.parent.replace(new RegExp(`${path}:(\\d+)`), `${path}:${newIdx}`)
      if (val.parent === path && typeof val.field === "number") {
        val.field = newIdx
      }
      if (getFullpath(val.parent, val.field) === path && typeof val.meta === "number") {
        val.meta = newIdx
      }
    } else if (key === "title" && typeof val === "string") {
      child[key] = val.replace(new RegExp(`${path}:(\\d+)`), `${path}:${newIdx}`)
    } else if (typeof val === "object") {
      updateModelListIds(val, path, newIdx)
    } else if (Array.isArray(val)) {
      val.forEach(item => updateModelListIds(item, path, newIdx))
    }
  })
  return child
}
