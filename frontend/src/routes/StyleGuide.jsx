import { useState } from "react"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Textarea } from "@/components/ui/textarea"
import { Checkbox } from "@/components/ui/checkbox"
import { Switch } from "@/components/ui/switch"
import { RadioGroup, RadioGroupItem } from "@/components/ui/radio-group"
import { Progress } from "@/components/ui/progress"
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select"
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog"
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
  AlertDialogTrigger,
} from "@/components/ui/alert-dialog"
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import {
  Accordion,
  AccordionContent,
  AccordionItem,
  AccordionTrigger,
} from "@/components/ui/accordion"
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table"
import { Toaster } from "@/components/ui/sonner"
import { toast } from "sonner"
import { Stepper } from "@/components/ui/stepper"
import { EmptyState } from "@/components/ui/empty-state"
import { SimpleBarChart } from "@/components/ui/chart"

function Section({ title, children }) {
  return (
    <section className="space-y-3">
      <h2 className="text-xl font-semibold">{title}</h2>
      <div className="flex flex-wrap items-center gap-4">{children}</div>
    </section>
  )
}

export default function StyleGuide() {
  const [progress] = useState(60)
  const chartData = [
    { name: "0-20", value: 2 },
    { name: "21-40", value: 5 },
    { name: "41-60", value: 9 },
    { name: "61-80", value: 7 },
    { name: "81-100", value: 4 },
  ]

  return (
    <div className="mx-auto max-w-4xl space-y-8 p-8">
      <h1 className="text-2xl font-bold">OMRFlow Style Guide</h1>
      <Toaster />

      <Section title="Buttons">
        <Button>Create test</Button>
        <Button variant="secondary">Generate sheets</Button>
        <Button variant="destructive">Delete</Button>
        <Button variant="outline">Scan</Button>
      </Section>

      <Section title="Form fields">
        <div className="grid w-full max-w-sm gap-2">
          <Label htmlFor="t">Title</Label>
          <Input id="t" placeholder="Test 1" />
          <Textarea placeholder="Description" />
        </div>
        <Checkbox /> <Switch />
        <RadioGroup defaultValue="a" className="flex gap-3">
          <RadioGroupItem value="a" id="a" />
          <RadioGroupItem value="b" id="b" />
        </RadioGroup>
      </Section>

      <Section title="Select (custom, not native)">
        <Select>
          <SelectTrigger className="w-48">
            <SelectValue placeholder="Subject" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="math">Math</SelectItem>
            <SelectItem value="sci">Science</SelectItem>
          </SelectContent>
        </Select>
      </Section>

      <Section title="Modal / Confirm / Menu / Toast">
        <Dialog>
          <DialogTrigger asChild>
            <Button>Open modal</Button>
          </DialogTrigger>
          <DialogContent>
            <DialogHeader>
              <DialogTitle>Custom modal</DialogTitle>
            </DialogHeader>
            <p className="text-sm">No native dialogs anywhere.</p>
          </DialogContent>
        </Dialog>

        <AlertDialog>
          <AlertDialogTrigger asChild>
            <Button variant="destructive">Confirm delete</Button>
          </AlertDialogTrigger>
          <AlertDialogContent>
            <AlertDialogHeader>
              <AlertDialogTitle>Delete this test?</AlertDialogTitle>
            </AlertDialogHeader>
            <AlertDialogFooter>
              <AlertDialogCancel>Cancel</AlertDialogCancel>
              <AlertDialogAction>Delete</AlertDialogAction>
            </AlertDialogFooter>
          </AlertDialogContent>
        </AlertDialog>

        <DropdownMenu>
          <DropdownMenuTrigger asChild>
            <Button variant="outline">Actions</Button>
          </DropdownMenuTrigger>
          <DropdownMenuContent>
            <DropdownMenuItem>Edit</DropdownMenuItem>
            <DropdownMenuItem>Duplicate</DropdownMenuItem>
          </DropdownMenuContent>
        </DropdownMenu>

        <Button onClick={() => toast.success("Saved")}>Show toast</Button>
      </Section>

      <Section title="Tabs / Accordion">
        <Tabs defaultValue="one" className="w-full">
          <TabsList>
            <TabsTrigger value="one">Overview</TabsTrigger>
            <TabsTrigger value="two">Settings</TabsTrigger>
          </TabsList>
          <TabsContent value="one">Overview content</TabsContent>
          <TabsContent value="two">Settings content</TabsContent>
        </Tabs>
        <Accordion type="single" collapsible className="w-full">
          <AccordionItem value="a1">
            <AccordionTrigger>Analytics</AccordionTrigger>
            <AccordionContent>Improvement across retests.</AccordionContent>
          </AccordionItem>
        </Accordion>
      </Section>

      <Section title="Table / Progress / Stepper">
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>Student</TableHead>
              <TableHead>Score</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            <TableRow>
              <TableCell>Asha</TableCell>
              <TableCell>18/20</TableCell>
            </TableRow>
          </TableBody>
        </Table>
        <div className="w-64">
          <Progress value={progress} />
        </div>
        <Stepper steps={["Details", "Questions", "Generate"]} current={1} />
      </Section>

      <Section title="Empty state / Chart">
        <EmptyState
          title="No tests yet"
          description="Create your first MCQ test to get started."
          action={<Button>Create test</Button>}
        />
        <div className="w-full max-w-md">
          <SimpleBarChart data={chartData} />
        </div>
      </Section>
    </div>
  )
}
