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
    const dictItemKeys = dash_clientside.callback_context.inputs_list[2].reduce((current, x) => {
      current[`${x.id.parent}:${x.id.field}:${x.id.meta}`.replace(/^:/, "")] = x.value
      return current
    }, {})
    const formData = inputs.reduce((acc, val) => {
        const key = `${val.id.parent}:${val.id.field}`.replace(/^:/, "")
        const parts = key.split(":")
        let pointer = acc
        const matchingDictKeys = Object.keys(dictItemKeys)
          .filter(k => key.startsWith(k))
          .sort((a, b) => b.split(":").length - a.split(":").length)
        const [nthPart, newKey] = matchingDictKeys.length > 0
          ? [matchingDictKeys[0].split(":").length, dictItemKeys[matchingDictKeys[0]]]
          : [null, null]
        parts.forEach((part, i) => {
            if (i + 1 === nthPart) {
              part = newKey || part
            }
            if (i === parts.length - 1) {
              pointer[part] = val.value
            } else {
                const prt = i + 1 !== nthPart && /^\d+$/.test(part) ? Number(part) : part
                if (!pointer[prt]) {
                    pointer[prt] = i + 2 !== nthPart && /^\d+$/.test(parts[i + 1]) ? [] : {}
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
  updateModalTitle: (val, id) => {
    const out = val != null ? String(val) : dash_clientside.no_update
    try {
      dash_clientside.set_props(
        {...id, component: "_pydf-list-field-modal-text"},
        {"children": out}
      )
    } catch (e) {
      //
    }
    return out
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
    const templateCopy = updateModelListIds(JSON.parse(template), path, current.length)
    templateCopy.props.key = uuid4()
    return [...current, templateCopy]
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

const uuid4 = () => {
  return "10000000-1000-4000-8000-100000000000".replace(/[018]/g, c =>
    (+c ^ crypto.getRandomValues(new Uint8Array(1))[0] & 15 >> +c / 4).toString(16)
  );
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
    } else if (typeof val === "string" && val.startsWith("uuid:")) {
      child[key] = `uuid:${uuid4()}`
    } else if (typeof val === "object") {
      updateModelListIds(val, path, newIdx)
    } else if (Array.isArray(val)) {
      val.forEach(item => updateModelListIds(item, path, newIdx))
    }
  })
  return child
}
