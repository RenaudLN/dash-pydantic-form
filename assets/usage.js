window.dash_clientside = window.dash_clientside || {}

dash_clientside.pydf_usage = {
  getSpecies: (allOptions, rowData, params) => {
    if ((params.dogNames || []).includes(rowData.name)) return allOptions.filter(x => x.value == "dog")
    if ((params.catNames || []).includes(rowData.name)) return allOptions.filter(x => x.value == "cat")
    return allOptions
  }
}
