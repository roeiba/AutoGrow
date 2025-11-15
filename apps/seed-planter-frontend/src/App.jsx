import { useState } from 'react'
import { Sparkles, Github, GitPullRequest, FileText, CheckCircle, XCircle, Loader2 } from 'lucide-react'
import { useSeedPlanter } from './hooks/useSeedPlanter'

function App() {
  const [projectIdea, setProjectIdea] = useState('')
  const { plantProject, progress, error, isPlanting } = useSeedPlanter()

  const handleSubmit = async (e) => {
    e.preventDefault()
    if (projectIdea.trim().length < 10) {
      return
    }
    await plantProject(projectIdea)
  }

  const getStatusIcon = (status) => {
    switch (status) {
      case 'completed':
        return <CheckCircle className="w-5 h-5 text-green-500" />
      case 'failed':
        return <XCircle className="w-5 h-5 text-red-500" />
      default:
        return <Loader2 className="w-5 h-5 text-primary-500 animate-spin" />
    }
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-primary-50 via-white to-purple-50">
      {/* Header */}
      <header className="bg-white border-b border-gray-200">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6">
          <div className="flex items-center gap-3">
            <Sparkles className="w-8 h-8 text-primary-600" />
            <div>
              <h1 className="text-2xl font-bold text-gray-900">SeedGPT Sandbox</h1>
              <p className="text-sm text-gray-600">Watch AI build your project in real-time</p>
            </div>
          </div>
        </div>
      </header>

      {/* Main Content */}
      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-12">
        <div className="grid lg:grid-cols-2 gap-8">
          {/* Input Section */}
          <div className="space-y-6">
            <div className="card">
              <h2 className="text-xl font-semibold mb-4">Try AutoGrow Now</h2>
              <p className="text-gray-600 mb-6">
                Describe your project idea and watch AI generate a complete repository with structure, 
                issues, and pull requests - all in under a minute.
              </p>

              <form onSubmit={handleSubmit} className="space-y-4">
                <div>
                  <label htmlFor="project-idea" className="block text-sm font-medium text-gray-700 mb-2">
                    Project Idea
                  </label>
                  <textarea
                    id="project-idea"
                    rows={4}
                    className="input-field resize-none"
                    placeholder="E.g., A task management app for remote teams with real-time collaboration..."
                    value={projectIdea}
                    onChange={(e) => setProjectIdea(e.target.value)}
                    disabled={isPlanting}
                    minLength={10}
                    maxLength={500}
                  />
                  <p className="text-xs text-gray-500 mt-1">
                    {projectIdea.length}/500 characters (minimum 10)
                  </p>
                </div>

                <button
                  type="submit"
                  className="btn-primary w-full flex items-center justify-center gap-2"
                  disabled={isPlanting || projectIdea.trim().length < 10}
                >
                  {isPlanting ? (
                    <>
                      <Loader2 className="w-5 h-5 animate-spin" />
                      Planting Project...
                    </>
                  ) : (
                    <>
                      <Sparkles className="w-5 h-5" />
                      Generate Demo Project
                    </>
                  )}
                </button>
              </form>
            </div>

            {/* Features */}
            <div className="card">
              <h3 className="font-semibold mb-4">What You'll Get:</h3>
              <ul className="space-y-3">
                <li className="flex items-start gap-3">
                  <Github className="w-5 h-5 text-primary-600 mt-0.5 flex-shrink-0" />
                  <div>
                    <p className="font-medium">GitHub Repository</p>
                    <p className="text-sm text-gray-600">Temporary repo with full project structure</p>
                  </div>
                </li>
                <li className="flex items-start gap-3">
                  <FileText className="w-5 h-5 text-primary-600 mt-0.5 flex-shrink-0" />
                  <div>
                    <p className="font-medium">Initial Issues</p>
                    <p className="text-sm text-gray-600">AI-generated tasks to get started</p>
                  </div>
                </li>
                <li className="flex items-start gap-3">
                  <GitPullRequest className="w-5 h-5 text-primary-600 mt-0.5 flex-shrink-0" />
                  <div>
                    <p className="font-medium">First Pull Request</p>
                    <p className="text-sm text-gray-600">Example PR showing AI capabilities</p>
                  </div>
                </li>
              </ul>
            </div>
          </div>

          {/* Progress Section */}
          <div className="space-y-6">
            {error && (
              <div className="card border-red-200 bg-red-50">
                <div className="flex items-start gap-3">
                  <XCircle className="w-5 h-5 text-red-500 mt-0.5 flex-shrink-0" />
                  <div>
                    <h3 className="font-semibold text-red-900">Error</h3>
                    <p className="text-sm text-red-700 mt-1">{error}</p>
                  </div>
                </div>
              </div>
            )}

            {progress && (
              <div className="card">
                <h3 className="text-lg font-semibold mb-4">Progress</h3>
                
                {/* Progress Bar */}
                <div className="mb-6">
                  <div className="flex justify-between text-sm mb-2">
                    <span className="text-gray-600">{progress.message}</span>
                    <span className="font-medium text-primary-600">{progress.progress_percent}%</span>
                  </div>
                  <div className="w-full bg-gray-200 rounded-full h-2">
                    <div
                      className="bg-primary-600 h-2 rounded-full transition-all duration-500"
                      style={{ width: `${progress.progress_percent}%` }}
                    />
                  </div>
                </div>

                {/* Status Steps */}
                <div className="space-y-3">
                  <StatusStep
                    icon={getStatusIcon(progress.status === 'creating_repo' ? 'in_progress' : progress.progress_percent > 10 ? 'completed' : 'pending')}
                    title="Creating Repository"
                    active={progress.status === 'creating_repo'}
                    completed={progress.progress_percent > 10}
                  />
                  <StatusStep
                    icon={getStatusIcon(progress.status === 'generating_structure' ? 'in_progress' : progress.progress_percent > 30 ? 'completed' : 'pending')}
                    title="Generating Structure"
                    active={progress.status === 'generating_structure'}
                    completed={progress.progress_percent > 30}
                  />
                  <StatusStep
                    icon={getStatusIcon(progress.status === 'creating_issues' ? 'in_progress' : progress.progress_percent > 60 ? 'completed' : 'pending')}
                    title="Creating Issues"
                    active={progress.status === 'creating_issues'}
                    completed={progress.progress_percent > 60}
                  />
                  <StatusStep
                    icon={getStatusIcon(progress.status === 'creating_pr' ? 'in_progress' : progress.progress_percent > 80 ? 'completed' : 'pending')}
                    title="Creating Pull Request"
                    active={progress.status === 'creating_pr'}
                    completed={progress.progress_percent > 80}
                  />
                </div>

                {/* Results */}
                {progress.status === 'completed' && (
                  <div className="mt-6 pt-6 border-t border-gray-200 space-y-3">
                    <h4 className="font-semibold text-green-700 flex items-center gap-2">
                      <CheckCircle className="w-5 h-5" />
                      Sandbox Ready!
                    </h4>
                    {progress.repo_url && (
                      <a
                        href={progress.repo_url}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="flex items-center gap-2 text-primary-600 hover:text-primary-700 font-medium"
                      >
                        <Github className="w-4 h-4" />
                        View Repository
                      </a>
                    )}
                    {progress.pr_url && (
                      <a
                        href={progress.pr_url}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="flex items-center gap-2 text-primary-600 hover:text-primary-700 font-medium"
                      >
                        <GitPullRequest className="w-4 h-4" />
                        View Pull Request
                      </a>
                    )}
                  </div>
                )}
              </div>
            )}

            {!progress && !isPlanting && (
              <div className="card text-center py-12">
                <Sparkles className="w-16 h-16 text-gray-300 mx-auto mb-4" />
                <p className="text-gray-500">
                  Enter a project idea to see AutoGrow in action
                </p>
              </div>
            )}
          </div>
        </div>
      </main>

      {/* Footer */}
      <footer className="mt-20 border-t border-gray-200 bg-white">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
          <p className="text-center text-gray-600 text-sm">
            Powered by <span className="font-semibold">SeedGPT</span> - Autonomous AI-driven development
          </p>
        </div>
      </footer>
    </div>
  )
}

function StatusStep({ icon, title, active, completed }) {
  return (
    <div className={`flex items-center gap-3 p-3 rounded-lg transition-colors ${
      active ? 'bg-primary-50' : completed ? 'bg-green-50' : 'bg-gray-50'
    }`}>
      {icon}
      <span className={`font-medium ${
        active ? 'text-primary-700' : completed ? 'text-green-700' : 'text-gray-500'
      }`}>
        {title}
      </span>
    </div>
  )
}

export default App
