import React from 'react'
import { render, screen, fireEvent } from '@testing-library/react'
import '@testing-library/jest-dom'
import { Button } from '../Button'

describe('Button Component', () => {
  it('renders with default props', () => {
    render(<Button>Test Button</Button>)
    const button = screen.getByRole('button', { name: /test button/i })
    expect(button).toBeInTheDocument()
    expect(button).toHaveClass('bg-richmond-river')
  })

  it('renders with different variants', () => {
    const { rerender } = render(<Button variant="secondary">Secondary</Button>)
    let button = screen.getByRole('button')
    expect(button).toHaveClass('bg-transparent', 'text-richmond-river', 'border-2')

    rerender(<Button variant="ghost">Ghost</Button>)
    button = screen.getByRole('button')
    expect(button).toHaveClass('bg-transparent', 'text-gray-700')

    rerender(<Button variant="destructive">Destructive</Button>)
    button = screen.getByRole('button')
    expect(button).toHaveClass('bg-richmond-brick')
  })

  it('renders with different sizes', () => {
    const { rerender } = render(<Button size="sm">Small</Button>)
    let button = screen.getByRole('button')
    expect(button).toHaveClass('h-8', 'px-3')

    rerender(<Button size="lg">Large</Button>)
    button = screen.getByRole('button')
    expect(button).toHaveClass('h-12', 'px-6')

    rerender(<Button size="icon">Icon</Button>)
    button = screen.getByRole('button')
    expect(button).toHaveClass('h-10', 'w-10')
  })

  it('handles click events', () => {
    const handleClick = jest.fn()
    render(<Button onClick={handleClick}>Click me</Button>)
    
    const button = screen.getByRole('button')
    fireEvent.click(button)
    
    expect(handleClick).toHaveBeenCalledTimes(1)
  })

  it('can be disabled', () => {
    const handleClick = jest.fn()
    render(<Button disabled onClick={handleClick}>Disabled</Button>)
    
    const button = screen.getByRole('button')
    expect(button).toBeDisabled()
    
    fireEvent.click(button)
    expect(handleClick).not.toHaveBeenCalled()
  })

  it('applies custom className', () => {
    render(<Button className="custom-class">Custom</Button>)
    const button = screen.getByRole('button')
    expect(button).toHaveClass('custom-class')
  })

  it('renders as child when asChild is true', () => {
    render(
      <Button asChild>
        <a href="/test">Link Button</a>
      </Button>
    )
    
    const link = screen.getByRole('link')
    expect(link).toBeInTheDocument()
    expect(link).toHaveAttribute('href', '/test')
  })
})