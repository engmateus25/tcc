describe('AquaMonitor shell', () => {
  it('loads the dashboard route', () => {
    cy.visit('/')
    cy.contains('AquaMonitor')
    cy.contains('Nível do Reservatório')
  })
})
