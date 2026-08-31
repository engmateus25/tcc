describe('AquaMonitor shell', () => {
  it('loads the dashboard route', () => {
    cy.visit('/')
    cy.contains('AquaMonitor')
    cy.contains('Nível do Reservatório')
  })

  it('uses a two-column home layout on desktop viewports', () => {
    [
      [1024, 768],
      [1440, 900],
    ].forEach(([width, height]) => {
      cy.viewport(width, height)
      cy.visit('/home')

      cy.get('[data-testid="home-responsive-grid"]').should('have.css', 'display', 'grid')
      cy.get('[data-testid="home-left-column"]').then(($left) => {
        cy.get('[data-testid="home-right-column"]').then(($right) => {
          const leftRect = $left[0].getBoundingClientRect()
          const rightRect = $right[0].getBoundingClientRect()
          expect(rightRect.left).to.be.greaterThan(leftRect.left + leftRect.width - 4)
        })
      })
    })
  })

  it('lets the shared header leave the viewport during content scroll', () => {
    cy.viewport(390, 700)
    cy.visit('/home')
    cy.get('[data-testid="app-scroll-header"]').should('be.visible')

    scrollIonContent(520)

    cy.get('[data-testid="app-scroll-header"]').should(($header) => {
      expect($header[0].getBoundingClientRect().bottom).to.be.lessThan(0)
    })
  })

  it('renders history filters as interactive controls and removes the AI assistant block', () => {
    cy.viewport(390, 800)
    cy.visit('/history')

    cy.get('[data-testid="period-filter"]').within(() => {
      cy.contains('button', '30 dias').click()
      cy.contains('button', '30 dias').should('have.attr', 'aria-pressed', 'true')
      cy.contains('button', '7 dias').should('have.attr', 'aria-pressed', 'false')
    })

    cy.get('[data-testid="history-type-filter"]').within(() => {
      cy.contains('button', 'Energia').click()
      cy.contains('button', 'Energia').should('have.attr', 'data-state', 'active')
      cy.contains('button', 'Água').should('have.attr', 'data-state', 'inactive')
    })

    cy.contains('Analise os dados do período atual com perguntas em linguagem natural').should('not.exist')
    cy.contains('button', 'Abrir Chat').should('not.exist')
  })
})

type ScrollableIonContent = HTMLElement & {
  scrollToPoint?: (x: number, y: number, duration?: number) => Promise<void>;
};

function scrollIonContent(y: number) {
  cy.get('ion-content').then(($content) => {
    const content = $content[0] as ScrollableIonContent
    if (content.scrollToPoint) {
      return content.scrollToPoint(0, y, 0)
    }
    content.scrollTop = y
    return undefined
  })
}
