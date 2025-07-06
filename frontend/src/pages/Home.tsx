import { Link } from 'react-router-dom'
import { Mic, FileText, Sparkles, Users } from 'lucide-react'
import { motion } from 'framer-motion'

export function Home() {
  return (
    <div className="min-h-[calc(100vh-4rem)]">
      {/* Hero Section */}
      <section className="relative bg-gradient-to-br from-richmond-river to-richmond-sunset overflow-hidden">
        <div className="absolute inset-0 bg-richmond-pattern opacity-10" />
        
        <div className="relative max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-24 lg:py-32">
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.6 }}
            className="text-center"
          >
            <h1 className="text-4xl md:text-6xl font-display font-bold text-white mb-6">
              Your Richmond Story,{' '}
              <span className="block text-richmond-magnolia-cream">Beautifully Told</span>
            </h1>
            <p className="text-xl text-richmond-dogwood-white opacity-90 max-w-3xl mx-auto mb-8">
              Transform your voice into compelling narratives that capture the essence of Richmond. 
              Our AI-powered platform helps you craft stories that resonate with your community.
            </p>
            <div className="flex flex-col sm:flex-row gap-4 justify-center">
              <Link to="/record" className="btn btn-primary bg-white text-richmond-river hover:bg-gray-100">
                <Mic className="w-5 h-5 mr-2" />
                Start with Voice
              </Link>
              <Link to="/templates" className="btn btn-secondary border-white text-white hover:bg-white hover:text-richmond-river">
                Browse Templates
              </Link>
            </div>
          </motion.div>
        </div>

        {/* Wave SVG */}
        <div className="absolute bottom-0 left-0 right-0">
          <svg viewBox="0 0 1440 120" className="w-full h-20 fill-gray-50">
            <path d="M0,96L48,90.7C96,85,192,75,288,69.3C384,64,480,64,576,69.3C672,75,768,85,864,85.3C960,85,1056,75,1152,69.3C1248,64,1344,64,1392,64L1440,64L1440,120L1392,120C1344,120,1248,120,1152,120C1056,120,960,120,864,120C768,120,672,120,576,120C480,120,384,120,288,120C192,120,96,120,48,120L0,120Z" />
          </svg>
        </div>
      </section>

      {/* Features Section */}
      <section className="py-16 lg:py-24">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="text-center mb-12">
            <h2 className="text-3xl font-display font-bold text-gray-900 mb-4">
              How It Works
            </h2>
            <p className="text-lg text-gray-600 max-w-2xl mx-auto">
              Three simple steps to transform your ideas into powerful Richmond stories
            </p>
          </div>

          <div className="grid md:grid-cols-3 gap-8">
            {[
              {
                icon: Mic,
                title: 'Speak Your Story',
                description: 'Simply record your voice or type your ideas. Our AI understands your vision.',
                color: 'text-richmond-sunset',
              },
              {
                icon: Sparkles,
                title: 'AI Enhancement',
                description: 'We enrich your story with Richmond context, quotes, and local flavor.',
                color: 'text-richmond-moss-green',
              },
              {
                icon: FileText,
                title: 'Publish & Share',
                description: 'Export your polished story in multiple formats ready for any platform.',
                color: 'text-richmond-river',
              },
            ].map((feature, index) => (
              <motion.div
                key={index}
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ duration: 0.6, delay: index * 0.1 }}
                className="card text-center group hover:shadow-lg"
              >
                <div className={`inline-flex p-3 rounded-lg bg-gray-50 ${feature.color} mb-4 group-hover:scale-110 transition-transform`}>
                  <feature.icon className="w-8 h-8" />
                </div>
                <h3 className="text-xl font-display font-semibold mb-2">{feature.title}</h3>
                <p className="text-gray-600">{feature.description}</p>
              </motion.div>
            ))}
          </div>
        </div>
      </section>

      {/* Community Section */}
      <section className="py-16 bg-richmond-magnolia-cream">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="grid lg:grid-cols-2 gap-12 items-center">
            <div>
              <h2 className="text-3xl font-display font-bold text-gray-900 mb-6">
                Join Richmond's Storytelling Community
              </h2>
              <p className="text-lg text-gray-600 mb-8">
                Connect with fellow Richmond storytellers, share your narratives, and discover 
                the rich tapestry of experiences that make our city unique. Every story matters, 
                and yours could inspire the next generation.
              </p>
              <div className="flex items-center space-x-8 text-sm">
                <div>
                  <div className="text-2xl font-bold text-richmond-river">500+</div>
                  <div className="text-gray-600">Stories Created</div>
                </div>
                <div>
                  <div className="text-2xl font-bold text-richmond-sunset">50+</div>
                  <div className="text-gray-600">Active Storytellers</div>
                </div>
                <div>
                  <div className="text-2xl font-bold text-richmond-moss-green">4.9</div>
                  <div className="text-gray-600">User Rating</div>
                </div>
              </div>
            </div>
            <div className="relative">
              <div className="absolute inset-0 bg-gradient-to-r from-richmond-river to-richmond-sunset rounded-lg transform rotate-3"></div>
              <div className="relative bg-white rounded-lg p-8 shadow-xl">
                <blockquote className="text-lg text-gray-700 italic">
                  "This platform helped me capture my family's 100-year history in Richmond 
                  in a way that truly honors our legacy. The AI understood the cultural nuances 
                  and helped me weave in historical context I didn't even know about."
                </blockquote>
                <div className="mt-4 flex items-center">
                  <div className="w-12 h-12 bg-richmond-sunset rounded-full flex items-center justify-center text-white font-bold">
                    MJ
                  </div>
                  <div className="ml-3">
                    <div className="font-semibold">Maria Johnson</div>
                    <div className="text-sm text-gray-600">Richmond Native</div>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* CTA Section */}
      <section className="py-16">
        <div className="max-w-4xl mx-auto text-center px-4 sm:px-6 lg:px-8">
          <h2 className="text-3xl font-display font-bold text-gray-900 mb-4">
            Ready to Tell Your Richmond Story?
          </h2>
          <p className="text-lg text-gray-600 mb-8">
            Join our community of storytellers and start creating narratives that matter.
          </p>
          <Link to="/record" className="btn btn-primary text-lg px-8 py-4">
            <Mic className="w-5 h-5 mr-2" />
            Start Recording Now
          </Link>
        </div>
      </section>
    </div>
  )
}